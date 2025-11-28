import numpy as np
from scipy.optimize import least_squares
from load_engine import AdvancedLoadMapper

class SoilStructureSolver:
    """
    MODULE 3: SOLVER (PHASE 2 - SCIPY OPTIMIZATION)
    Giải bài toán cân bằng lực trên nền đàn hồi sử dụng thuật toán tối ưu hóa phi tuyến.
    Method: Trust Region Reflective (TRF) via scipy.optimize.least_squares
    """
    def __init__(self, mesh_obj):
        self.mesh = mesh_obj
        self.load_mapper = AdvancedLoadMapper(mesh_obj)
    
    def _residual_function(self, params, X, Y, Ks, dA, V_target, Mx_target, My_target):
        """
        Hàm mục tiêu tính toán sai số (Residual) để AI tối ưu hóa.
        Params: [w0 (độ lún chuẩn), th_x (góc xoay trục X), th_y (góc xoay trục Y)]
        """
        w0, th_x, th_y = params
        
        # 1. Tính mặt phẳng lún (Kinematic Constraint)
        # w = w0 + y*th_x - x*th_y
        w_vec = w0 + Y * th_x - X * th_y
        
        # 2. Xử lý phi tuyến (Non-linearity): Nền đất chỉ chịu nén, không chịu kéo
        # Nếu w < 0 (hở đất) -> Áp lực = 0
        w_eff = np.maximum(w_vec, 0)
        
        # 3. Tính phản lực nền (Winkler Model)
        p_vec = w_eff * Ks
        F_spring = p_vec * dA
        
        # 4. Tính tổng phản lực và mô-men phản hồi
        V_react = np.sum(F_spring)
        Mx_react = np.sum(F_spring * Y)     # Moment quanh trục X
        My_react = np.sum(F_spring * (-X))  # Moment quanh trục Y (Lưu ý dấu -X theo quy tắc bàn tay phải)
        
        # 5. Trả về vector sai số (Residuals)
        # AI sẽ cố gắng đưa vector này về [0, 0, 0]
        err_V = V_target - V_react
        err_Mx = Mx_target - Mx_react
        err_My = My_target - My_react
        
        return np.array([err_V, err_Mx, err_My])

    def solve_equilibrium(self, specs, physics_results, chassis_angle=0):
        # 1. Chuyển đổi đơn vị & Đảo dấu Moment (SIGN FIX)
        g = 9.81
        
        # [FIX] Đảo dấu Mx và My để khớp hệ tọa độ hiển thị
        # Physics trả về Moment tác dụng (Action), Solver cần Moment phản hồi (Reaction)
        # hoặc do quy ước trục tọa độ ngược nhau giữa Physics (Z-up) và Grid (2D Plane).
        # Việc đảo dấu này đảm bảo: Quay phải -> Áp lực sang phải. Quay trước -> Áp lực lên trên.
        V_load_kN = physics_results['V_total_ton'] * g
        Mx_load_kNm = -physics_results['Mx_roll_Tm'] * g  # Đảo dấu
        My_load_kNm = -physics_results['My_pitch_Tm'] * g  # Đảo dấu
        
        # 2. Tạo mặt nạ vị trí xích
        self.load_mapper.apply_crane_rotation(
            specs['track_L'], specs['track_W'], specs['track_gauge'],
            chassis_angle, 1, 1 
        )
        
        # Lấy mask các điểm thuộc dải xích
        track_nodes_mask = (self.load_mapper.load_matrix > 0) & self.mesh.active_mask
        
        # EDGE CASE: Nếu xích nằm hoàn toàn ngoài tấm lót
        if np.sum(track_nodes_mask) == 0:
            return None, "Lỗi: Xích nằm ngoài vùng lưới tính toán (Mats/Ground)!"

        # Trích xuất dữ liệu vector (Vectorization) để tăng tốc độ tính toán
        X_i = self.mesh.nodes_X[track_nodes_mask]
        Y_i = self.mesh.nodes_Y[track_nodes_mask]
        Ks_i = self.mesh.Ks_matrix[track_nodes_mask] 
        dA = self.mesh.dA 
        
        # 3. Ước lượng điểm bắt đầu (Initial Guess)
        # Giả sử lún đều, chưa xoay. w0 = Lực / (Tổng độ cứng)
        k_total = np.sum(Ks_i) * dA
        w0_guess = V_load_kN / k_total if k_total > 0 else 0.01
        params0 = [w0_guess, 0.0, 0.0] # [w0, th_x, th_y]
        
        # 4. GỌI THUẬT TOÁN TỐI ƯU HÓA (CORE AI)
        # Sử dụng 'trf' (Trust Region Reflective) cho bài toán có ràng buộc và phi tuyến
        try:
            result = least_squares(
                self._residual_function,
                params0,
                args=(X_i, Y_i, Ks_i, dA, V_load_kN, Mx_load_kNm, My_load_kNm),
                method='trf',
                ftol=1e-6,      # Độ chính xác mục tiêu (Phase 2 requirement)
                xtol=1e-6,
                gtol=1e-6,
                max_nfev=100    # Giới hạn số lần thử
            )
        except Exception as e:
            return None, f"Solver Error: {str(e)}"

        if not result.success and result.cost > 1.0:
            # Nếu sai số vẫn lớn hơn 1.0 đơn vị sau khi chạy xong
            return None, "Không tìm thấy điểm cân bằng hội tụ (Unstable Ground)!"

        # 5. Trích xuất kết quả cuối cùng
        w0_opt, th_x_opt, th_y_opt = result.x
        
        # Tính lại bản đồ áp lực (Full Map Reconstruction)
        full_pressure = np.zeros_like(self.mesh.nodes_X)
        
        # Tính độ lún tại các điểm active
        w_final_vec = w0_opt + Y_i * th_x_opt - X_i * th_y_opt
        p_final_vec = np.maximum(w_final_vec, 0) * Ks_i
        
        # Map ngược lại vào lưới 2D
        full_pressure[track_nodes_mask] = p_final_vec
        
        # 6. Trả về kết quả kèm Metadata cho UI
        return {
            "pressure_map": full_pressure,
            "settlement_max": np.max(w_final_vec),
            "pressure_max": np.max(p_final_vec),
            "contact_ratio": np.sum(p_final_vec > 0) / len(p_final_vec) * 100,
            # Metadata Phase 2
            "solver_iters": result.nfev,  # Số lần tính toán
            "solver_status": result.status,
            "solver_cost": result.cost    # Tổng bình phương sai số còn lại
        }, None