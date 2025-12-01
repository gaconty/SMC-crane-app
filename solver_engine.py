import numpy as np
from scipy.optimize import least_squares

class SoilStructureSolver:
    def __init__(self, mesh_generator, load_mapper=None):
        self.mesh = mesh_generator
        if load_mapper is None:
            from load_engine import AdvancedLoadMapper
            self.load_mapper = AdvancedLoadMapper(self.mesh)
        else:
            self.load_mapper = load_mapper

    def _residual_function(self, params, X, Y, Ks, dA, V_load, Mx_load, My_load):
        w0, th_x, th_y = params
        
        # Settlement plane
        w = w0 + Y * th_x - X * th_y
        
        # Contact pressure (Winkler model: p = k * w)
        # Only where w > 0 (contact)
        p = np.maximum(w, 0) * Ks
        
        # Forces and Moments from ground reaction
        F_ground = np.sum(p) * dA
        Mx_ground = np.sum(p * Y) * dA
        My_ground = np.sum(-p * X) * dA 
        
        # Residuals (Equilibrium: Ground Reaction - Load = 0)
        res_F = F_ground - V_load
        res_Mx = Mx_ground - Mx_load
        res_My = My_ground - My_load
        
        return [res_F, res_Mx, res_My]

    def solve_equilibrium(self, specs, physics_results, chassis_angle=0):
        g = 9.81
        # Calculate V_load_kN from physics results
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
                max_nfev=1000    # Giới hạn số lần thử (Increased for robustness)
            )
        except Exception as e:
            return None, f"Solver Error: {str(e)}"

        if not result.success and result.cost > 1.0:
            # Nếu sai số vẫn lớn hơn 1.0 đơn vị sau khi chạy xong
            return None, f"Không tìm thấy điểm cân bằng hội tụ (Unstable Ground)! Cost={result.cost:.2f}"

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