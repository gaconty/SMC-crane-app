import numpy as np
import pandas as pd
from scipy.optimize import minimize
from config import G_CONST, SOIL_KS_DEFAULT

# Try importing ML libraries (Handle case if not installed yet)
try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer, Categorical
    from skopt.utils import use_named_args
    HAS_SKOPT = True
except ImportError:
    HAS_SKOPT = False

try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from crane_physics import AdvancedCranePhysics
from mesh_engine import AdvancedMeshGenerator
from solver_engine import SoilStructureSolver
from crane_physics import AdvancedCranePhysics
from mesh_engine import AdvancedMeshGenerator
from solver_engine import SoilStructureSolver
from unified_data import get_processed_specs
from backend.ai_learning import CraneAILearning

class OfflineAIAgent:
    """
    AI AGENT (OFFLINE MODE)
    Cung cấp các tính năng thông minh chạy cục bộ:
    1. Tối ưu hóa cấu hình (Bayesian Optimization)
    2. Dự đoán tham số đất (Local Regression)
    3. Phân tích rủi ro (Monte Carlo Simulation)
    """
    def __init__(self):
        self.soil_model = None
        self._train_dummy_soil_model()
        # Integration: Load Learning AI
        self.learner = CraneAILearning()

    def _train_dummy_soil_model(self):
        """
        Huấn luyện mô hình dự đoán đất đơn giản (Demo).
        Trong thực tế, sẽ load từ file .pkl đã train trước.
        """
        if not HAS_SKLEARN: return
        
        # Dữ liệu mẫu: [SoilType_Id, Moisture_Id] -> [Ks, Limit_P]
        # SoilType: 0=Clay, 1=Sand, 2=Silt, 3=Gravel
        # Moisture: 0=Low, 1=Med, 2=High
        X = np.array([
            [0, 0], [0, 1], [0, 2], # Clay
            [1, 0], [1, 1], [1, 2], # Sand
            [2, 0], [2, 1], [2, 2], # Silt
            [3, 0], [3, 1], [3, 2]  # Gravel
        ])
        # Target: Ks (kN/m3), Limit_P (t/m2)
        y = np.array([
            [8000, 15], [5000, 10], [3000, 5],   # Clay
            [20000, 30], [15000, 25], [10000, 15], # Sand
            [12000, 20], [8000, 15], [5000, 8],   # Silt
            [50000, 50], [40000, 40], [30000, 30] # Gravel
        ])
        
        self.soil_model = RandomForestRegressor(n_estimators=10, random_state=42)
        self.soil_model.fit(X, y)

    def predict_soil_params(self, soil_type_str, moisture_str):
        """
        Dự đoán Ks và P_allow dựa trên loại đất và độ ẩm.
        """
        if not HAS_SKLEARN or self.soil_model is None:
            return SOIL_KS_DEFAULT, 20.0 # Fallback
            
        type_map = {'Clay': 0, 'Sand': 1, 'Silt': 2, 'Gravel': 3}
        moist_map = {'Low': 0, 'Medium': 1, 'High': 2}
        
        t_id = type_map.get(soil_type_str, 1)
        m_id = moist_map.get(moisture_str, 1)
        
        pred = self.soil_model.predict([[t_id, m_id]])[0]
        return pred[0], pred[1] # Ks, P_allow

    def predict_pressure_smart(self, load_mass, radius, boom_len, slew_angle, soil_ks, cwt_mass, mat_L, mat_W):
        """
        Dự đoán áp lực sử dụng mô hình AI đã học (Learning AI).
        Nhanh hơn và chính xác hơn theo thời gian so với tính toán vật lý thuần túy.
        """
        if not self.learner.is_trained:
            return None, "Mô hình AI chưa được huấn luyện đủ dữ liệu."
            
        inputs = {
            'load_mass': load_mass,
            'radius': radius,
            'boom_len': boom_len,
            'slew_angle': slew_angle,
            'soil_ks': soil_ks,
            'cwt_mass': cwt_mass,
            'mat_L': mat_L,
            'mat_W': mat_W
        }
        
        res = self.learner.predict(inputs)
        if res:
            return res['p_max'], None
        return None, "Lỗi dự đoán AI"

    def optimize_configuration(self, base_specs, load_mass, radius, boom_angle, slew_angle, soil_ks, target_p_allow):
        """
        Tìm cấu hình Mat (L, W) tối ưu để P_max <= P_allow với chi phí thấp nhất.
        Sử dụng Bayesian Optimization (skopt).
        """
        if not HAS_SKOPT:
            return None, "Thư viện scikit-optimize chưa được cài đặt."

        # 1. Định nghĩa không gian tìm kiếm (Search Space)
        # Mat Length: 2.0m -> 12.0m
        # Mat Width: 1.0m -> 4.0m
        space = [
            Real(2.0, 12.0, name='mat_L'),
            Real(1.0, 4.0, name='mat_W')
        ]

        # 2. Chuẩn bị Physics State (Tính 1 lần vì Load không đổi)
        physics_engine = AdvancedCranePhysics(base_specs)
        phys_res = physics_engine.calculate_state(load_mass, boom_angle, slew_angle)

        # 3. Hàm Mục tiêu (Objective Function)
        @use_named_args(space)
        def objective(mat_L, mat_W):
            # A. Setup Simulation với tham số thử nghiệm
            # Rounding để thực tế hơn (bước 0.5m)
            mat_L = round(mat_L * 2) / 2
            mat_W = round(mat_W * 2) / 2
            
            # Update Specs cho Solver
            solve_specs = base_specs.copy()
            # Giả sử dùng Mat cho cả 2 bên nếu cần
            # Logic đơn giản: Nếu Mat > Track -> Dùng Mat làm kích thước tiếp xúc
            sim_L = max(solve_specs['track_L'], mat_L)
            sim_W = max(solve_specs['track_W'], mat_W)
            
            # Tạo Mesh
            # Optimization: Use AI Model if available and trained
            if self.learner.is_trained:
                # Use AI prediction as a fast surrogate
                # Note: This is an approximation. For final validation, we might want to run physics once at the end.
                inputs = {
                    'load_mass': load_mass, 'radius': radius, 'boom_len': base_specs['boom_len'],
                    'slew_angle': slew_angle, 'soil_ks': soil_ks, 'cwt_mass': base_specs['cwt_mass'],
                    'mat_L': mat_L, 'mat_W': mat_W
                }
                pred_res = self.learner.predict(inputs)
                if pred_res:
                    p_max = pred_res['p_max']
                    
                    # Cost & Penalty Logic (Same as below)
                    cost = mat_L * mat_W 
                    if p_max > target_p_allow:
                        penalty = (p_max - target_p_allow) * 1000
                    else:
                        penalty = 0
                    return cost + penalty

            # Fallback to Physics Engine if AI not trained
            mesh_gen = AdvancedMeshGenerator(mesh_size=0.5) # Coarse mesh for speed optimization
            mesh_gen.create_rectangular_mesh(sim_L*1.5, solve_specs['track_gauge']*2.0, default_Ks=soil_ks)
            
            # Solver
            solver = SoilStructureSolver(mesh_gen)
            
            # Truyền kích thước Mat vào specs để load mapper dùng (nếu logic solver hỗ trợ)
            # Ở đây ta hack nhẹ: update track dimensions tạm thời để mô phỏng Mat
            solve_specs['track_L'] = mat_L
            solve_specs['track_W'] = mat_W
            
            try:
                res, _ = solver.solve_equilibrium(solve_specs, phys_res)
                if res is None: return 1e6 # Penalty for failure
                
                p_max = res['pressure_max'] / G_CONST # t/m2
                
                # B. Tính Cost & Penalty
                # Cost = Diện tích tấm lót (đại diện cho chi phí)
                cost = mat_L * mat_W 
                
                # Penalty: Nếu P_max > P_allow -> Phạt nặng
                if p_max > target_p_allow:
                    penalty = (p_max - target_p_allow) * 1000 # Phạt 1000 điểm mỗi tấn vượt
                else:
                    penalty = 0
                    
                return cost + penalty
                
            except Exception:
                return 1e6 # Penalty for crash

        # 4. Chạy Tối ưu hóa (Bayesian Optimization)
        res_gp = gp_minimize(objective, space, n_calls=15, random_state=42)

        # 5. Trả về kết quả
        best_L = round(res_gp.x[0] * 2) / 2
        best_W = round(res_gp.x[1] * 2) / 2
        
        return {
            "optimal_L": best_L,
            "optimal_W": best_W,
            "min_cost_score": res_gp.fun
        }, None

    def run_risk_analysis(self, base_specs, load_mass, radius, boom_angle, slew_angle, soil_ks, target_p_allow, n_simulations=100):
        """
        Chạy mô phỏng Monte Carlo để đánh giá rủi ro.
        Biến thiên: Tải trọng (+/- 5%), Ks (+/- 20%), Radius (+/- 0.5m)
        """
        results = []
        failures = 0
        
        # 1. Tạo dữ liệu ngẫu nhiên (Vectorized generation)
        # Load: Mean=load_mass, Std=5%
        loads = np.random.normal(load_mass, load_mass * 0.05, n_simulations)
        
        # Radius: Mean=radius, Std=0.5m
        radii = np.random.normal(radius, 0.5, n_simulations)
        
        # Ks: Mean=soil_ks, Std=20%
        kss = np.random.normal(soil_ks, soil_ks * 0.2, n_simulations)
        
        # 2. Physics Engine (Reuse instance to save init time if possible, but specs change slightly if radius changes)
        # Tuy nhiên, radius thay đổi -> boom angle thay đổi -> physics thay đổi.
        
        physics_engine = AdvancedCranePhysics(base_specs)
        
        # Mesh Gen (Reuse object, just update Ks)
        mesh_gen = AdvancedMeshGenerator(mesh_size=0.5) # Coarse
        # Pre-create mesh structure
        sim_L = base_specs['track_L']
        mesh_gen.create_rectangular_mesh(sim_L*1.5, base_specs['track_gauge']*2.0, default_Ks=soil_ks)
        solver = SoilStructureSolver(mesh_gen)
        
        for i in range(n_simulations):
            # A. Update Physics Inputs
            # Recalculate boom angle based on new radius (approx)
            # cos(theta) = (R - pivot) / L_boom
            dist = radii[i] - base_specs['pivot_x']
            # Clamp dist to boom_len
            dist = min(dist, base_specs['boom_len'] * 0.99)
            b_angle = np.degrees(np.arccos(dist / base_specs['boom_len']))
            
            phys_res = physics_engine.calculate_state(loads[i], b_angle, slew_angle)
            
            # B. Update Solver Inputs
            # Update Ks matrix directly without recreating mesh
            mesh_gen.Ks_matrix[:] = kss[i]
            mesh_gen.Ks_matrix[~mesh_gen.active_mask] = 0
            
            # C. Solve
            try:
                res, _ = solver.solve_equilibrium(base_specs, phys_res)
                if res:
                    p_max = res['pressure_max'] / G_CONST
                    results.append(p_max)
                    if p_max > target_p_allow:
                        failures += 1
                else:
                    # Solver failed (unstable) -> Count as failure
                    failures += 1
                    results.append(target_p_allow * 2) # Dummy high value
            except:
                failures += 1
                results.append(target_p_allow * 2)

        # 3. Thống kê
        results = np.array(results)
        return {
            "mean_p_max": np.mean(results),
            "std_p_max": np.std(results),
            "max_p_max": np.max(results),
            "failure_prob_pct": (failures / n_simulations) * 100,
            "p_95_percentile": np.percentile(results, 95)
        }
