import numpy as np
from load_engine import AdvancedLoadMapper

class SoilStructureSolver:
    """
    MODULE 3: SOLVER (UNIT & SIGN CORRECTED)
    Giải bài toán cân bằng lực trên nền đàn hồi.
    Fix: Đảo dấu Moment để khớp hệ tọa độ hiển thị (Front=Top, Right=Right).
    """
    def __init__(self, mesh_obj):
        self.mesh = mesh_obj
        self.load_mapper = AdvancedLoadMapper(mesh_obj)
    
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
        track_nodes_mask = (self.load_mapper.load_matrix > 0) & self.mesh.active_mask
        
        if np.sum(track_nodes_mask) == 0:
            return None, "Xích nằm ngoài tấm lót!"

        X_i = self.mesh.nodes_X[track_nodes_mask]
        Y_i = self.mesh.nodes_Y[track_nodes_mask]
        Ks_i = self.mesh.Ks_matrix[track_nodes_mask] 
        dA = self.mesh.dA 
        
        # 3. Iterative Solver
        w0 = V_load_kN / (np.sum(Ks_i) * dA)
        th_x = 0.0
        th_y = 0.0
        
        for _ in range(50): 
            w_vec = w0 + Y_i * th_x - X_i * th_y
            w_eff = np.maximum(w_vec, 0)
            
            p_vec = w_eff * Ks_i 
            F_spring = p_vec * dA
            
            V_react = np.sum(F_spring)
            Mx_react = np.sum(F_spring * Y_i)
            My_react = np.sum(F_spring * (-X_i)) 
            
            err_V = V_load_kN - V_react
            err_Mx = Mx_load_kNm - Mx_react
            err_My = My_load_kNm - My_react
            
            active_idx = w_eff > 0
            if not np.any(active_idx): break

            k_eff = Ks_i
            k_v_total = np.sum(k_eff) * dA
            Ixx_eff = np.sum(k_eff * Y_i**2) * dA
            Iyy_eff = np.sum(k_eff * X_i**2) * dA
            
            if k_v_total == 0: break
            
            # Relaxation update
            w0 += (err_V / k_v_total) * 0.8
            th_x += (err_Mx / (Ixx_eff + 1e-3)) * 0.6
            th_y += (err_My / (Iyy_eff + 1e-3)) * 0.6
            
            if abs(err_V) < 0.1 and abs(err_Mx) < 1.0 and abs(err_My) < 1.0:
                break
                
        # 4. Xuất kết quả
        full_pressure = np.zeros_like(self.mesh.nodes_X)
        w_final = w0 + Y_i * th_x - X_i * th_y
        p_final = np.maximum(w_final, 0) * Ks_i
        full_pressure[track_nodes_mask] = p_final
        
        return {
            "pressure_map": full_pressure,
            "settlement_max": np.max(w_final),
            "pressure_max": np.max(p_final),
            "contact_ratio": np.sum(p_final > 0) / len(p_final) * 100
        }, None