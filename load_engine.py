"""
MODULE 2: VECTORIZED LOAD MAPPER (CORE ONLY)
Chức năng: Ánh xạ tải trọng cẩu lên lưới FEM.
Fix: Robust rounding to prevent asymmetry at 90/270 degrees.
"""

import numpy as np

class AdvancedLoadMapper:
    def __init__(self, mesh_obj):
        self.mesh = mesh_obj
        # Pre-compute grid for vectorization
        self.grid_coords = np.vstack((self.mesh.nodes_X.flatten(), 
                                      self.mesh.nodes_Y.flatten())).T
        self.load_matrix = None 

    def _get_rotated_mask(self, center_x, center_y, width, length, angle_rad):
        """Hàm nội bộ: Tạo mask hình chữ nhật xoay với cơ chế chống nhiễu số học"""
        shifted_points = self.grid_coords - np.array([center_x, center_y])
        
        # 1. Tính sin/cos chính xác
        cos_a = np.cos(-angle_rad)
        sin_a = np.sin(-angle_rad)
        
        # Xử lý nhiễu số học cho các góc vuông (0, 90, 180, 270)
        # Nếu giá trị quá nhỏ (gần 0), ép về 0 hẳn
        if abs(cos_a) < 1e-10: cos_a = 0.0
        if abs(sin_a) < 1e-10: sin_a = 0.0
        
        # 2. Xoay tọa độ
        X_local = shifted_points[:, 0] * cos_a - shifted_points[:, 1] * sin_a
        Y_local = shifted_points[:, 0] * sin_a + shifted_points[:, 1] * cos_a
        
        # 3. [CRITICAL FIX] Làm tròn tọa độ cục bộ để triệt tiêu sai số dấu phẩy động
        # Trước khi so sánh biên, làm tròn về 6 số thập phân (micromet)
        X_local = np.round(X_local, 6)
        Y_local = np.round(Y_local, 6)
        
        # 4. So sánh với biên có dung sai (Tolerance)
        tol = 1e-7
        
        mask_x = np.abs(X_local) <= (width / 2 + tol)
        mask_y = np.abs(Y_local) <= (length / 2 + tol)
        
        final_mask = (mask_x & mask_y).reshape(self.mesh.nodes_X.shape)
        return final_mask & self.mesh.active_mask

    def apply_crane_rotation(self, track_L, track_W, gauge, chassis_angle_deg, load_L, load_R):
        """
        Đặt tải lên lưới với góc xoay chassis_angle.
        """

        if abs(chassis_angle_deg - round(chassis_angle_deg)) < 1e-5:
            chassis_angle_deg = round(chassis_angle_deg)

        angle_rad = np.radians(chassis_angle_deg)
        
        # Ma trận xoay 2D cho tâm xích
        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)
        
        # Clean trig noise
        if abs(cos_a) < 1e-10: cos_a = 0.0
        if abs(sin_a) < 1e-10: sin_a = 0.0

        def rotate_point(x, y):
            return x*cos_a - y*sin_a, x*sin_a + y*cos_a

        # Tính tâm mới của 2 dải xích sau khi xoay cả xe
        cx_L, cy_L = rotate_point(-gauge/2, 0)
        cx_R, cy_R = rotate_point(gauge/2, 0)
        
        # Tạo mask
        mask_left = self._get_rotated_mask(cx_L, cy_L, track_W, track_L, angle_rad)
        mask_right = self._get_rotated_mask(cx_R, cy_R, track_W, track_L, angle_rad)
        
        # Reset và Gán tải
        self.load_matrix = np.zeros_like(self.mesh.nodes_X)
        area = track_L * track_W
        
        # Gán giá trị sơ bộ (Solver sẽ tinh chỉnh lại sau)
        if area > 0:
            self.load_matrix[mask_left] = (load_L * 10) / area
            self.load_matrix[mask_right] = (load_R * 10) / area
            
        return self.load_matrix