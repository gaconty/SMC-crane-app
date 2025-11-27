import numpy as np
from load_engine import AdvancedLoadMapper

class SoilStructureSolver:
    """
    MODULE 3: SOLVER
    Giải bài toán cân bằng lực trên nền đàn hồi (Winkler Foundation).
    Giả thiết: Bản xích cứng tuyệt đối (Rigid Plate) đặt trên nền lò xo.
    """
    def __init__(self, mesh_obj):
        self.mesh = mesh_obj
        self.load_mapper = AdvancedLoadMapper(mesh_obj)
    
    def solve_equilibrium(self, specs, physics_results, chassis_angle=0):
        """
        Tìm mặt phẳng lún cân bằng với tải trọng.
        :param specs: Thông số hình học xích (L, W, Gauge)
        :param physics_results: Kết quả từ Module Physics (V_total, Mx, My)
        :param chassis_angle: Góc quay của khung gầm so với tấm lót
        """
        # 1. Lấy tổng lực và moment tác dụng lên TÂM HỆ THỐNG XÍCH (0,0)
        # Lưu ý: Physics tính moment quanh tâm quay máy.
        V_load = physics_results['V_total_ton'] * 10 # Đổi ra kN (g=10 cho tròn hoặc 9.81)
        Mx_load = physics_results['Mx_roll_Tm'] * 10 # kNm
        My_load = physics_results['My_pitch_Tm'] * 10 # kNm
        
        # 2. Tạo mặt nạ vị trí xích trên lưới (Dùng LoadMapper cũ để lấy vị trí)
        # Ta cần biết nút nào thuộc xích để tính toán lò xo
        self.load_mapper.apply_crane_rotation(
            specs['track_L'], specs['track_W'], specs['track_gauge'],
            chassis_angle, 1, 1 # Dummy load để lấy mask
        )
        # Mask xích trái và phải
        # Trong load_mapper logic cũ chưa lưu mask riêng, ta tái tạo lại logic
        # Để đơn giản, ta lấy mask toàn bộ vùng có tải (load_matrix > 0)
        track_nodes_mask = (self.load_mapper.load_matrix > 0) & self.mesh.active_mask
        
        if np.sum(track_nodes_mask) == 0:
            return None, "Xích nằm ngoài tấm lót!"

        # Lấy tọa độ và độ cứng lò xo tại các nút thuộc xích
        X_i = self.mesh.nodes_X[track_nodes_mask]
        Y_i = self.mesh.nodes_Y[track_nodes_mask]
        Ks_i = self.mesh.Ks_matrix[track_nodes_mask] # kN/m3
        dA = self.mesh.dA # m2
        
        # 3. GIẢI BÀI TOÁN TỐI ƯU (ITERATIVE SOLVER)
        # Phương trình mặt phẳng lún: w(x,y) = w0 + theta_x * Y - theta_y * X
        # (Lưu ý dấu: theta_x xoay quanh trục X làm y thay đổi độ cao)
        
        # Ta cần tìm 3 ẩn số: [w0 (lún đều), theta_x (góc nghiêng ngang), theta_y (góc chúi dọc)]
        # Sao cho:
        # Sum(F_lo_xo) = V_load
        # Sum(M_lo_xo_x) = Mx_load
        # Sum(M_lo_xo_y) = My_load
        
        # Vì lò xo không chịu kéo (đất không giữ xích), nếu w(x,y) < 0 thì p = 0.
        # Do tính phi tuyến này (Separation), ta không giải hệ pt tuyến tính trực tiếp được
        # mà dùng phương pháp lặp Newton-Raphson hoặc đơn giản là Iterative Adjustment.
        
        # Khởi tạo giá trị ban đầu
        w0 = V_load / (np.sum(Ks_i) * dA)
        th_x = 0.0
        th_y = 0.0
        
        # Vòng lặp giải
        for _ in range(50): # 50 bước lặp thường là đủ hội tụ
            # Tính độ lún tại mọi điểm với bộ tham số hiện tại
            # w = w0 + y*th_x - x*th_y
            w_vec = w0 + Y_i * th_x - X_i * th_y
            
            # Áp dụng điều kiện biên: Đất chỉ chịu nén (w > 0)
            w_eff = np.maximum(w_vec, 0)
            
            # Tính phản lực nền
            p_vec = w_eff * Ks_i # kN/m2
            F_spring = p_vec * dA
            
            # Tính tổng lực và moment phản hồi
            V_react = np.sum(F_spring)
            Mx_react = np.sum(F_spring * Y_i)
            My_react = np.sum(F_spring * (-X_i)) # Dấu trừ do quy ước chiều moment
            
            # Tính sai số
            err_V = V_load - V_react
            err_Mx = Mx_load - Mx_react
            err_My = My_load - My_react
            
            # Cập nhật thông số (Relaxation factor 0.1 - 0.5 để ổn định)
            # Dùng ma trận độ cứng xấp xỉ của hệ để update (Jacoiban)
            # K_vertical ~ Sum(k*dA)
            # K_rot ~ Sum(k*r^2*dA)
            
            k_v_total = np.sum(Ks_i) * dA
            Ixx_eff = np.sum(Ks_i * Y_i**2) * dA
            Iyy_eff = np.sum(Ks_i * X_i**2) * dA
            
            if k_v_total == 0: break
            
            w0 += (err_V / k_v_total) * 0.8
            th_x += (err_Mx / (Ixx_eff + 1e-3)) * 0.5
            th_y += (err_My / (Iyy_eff + 1e-3)) * 0.5
            
            # Kiểm tra hội tụ
            if abs(err_V) < 0.1 and abs(err_Mx) < 1.0 and abs(err_My) < 1.0:
                break
                
        # 4. Xuất kết quả cuối cùng ra toàn lưới
        full_pressure = np.zeros_like(self.mesh.nodes_X)
        
        # Tính lại cho toàn bộ điểm thuộc track
        w_final = w0 + Y_i * th_x - X_i * th_y
        p_final = np.maximum(w_final, 0) * Ks_i
        
        # Gán ngược lại vào ma trận 2D
        full_pressure[track_nodes_mask] = p_final
        
        return {
            "pressure_map": full_pressure,
            "settlement_max": np.max(w_final),
            "pressure_max": np.max(p_final),
            "contact_ratio": np.sum(p_final > 0) / len(p_final) * 100 # Diện tích tiếp xúc %
        }, None