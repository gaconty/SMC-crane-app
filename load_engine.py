"""
MODULE 2: VECTORIZED LOAD MAPPER (CORE ONLY)
Chức năng: Ánh xạ tải trọng cẩu lên lưới FEM.
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
        """Hàm nội bộ: Tạo mask hình chữ nhật xoay"""
        shifted_points = self.grid_coords - np.array([center_x, center_y])
        
        cos_a = np.cos(-angle_rad)
        sin_a = np.sin(-angle_rad)
        
        X_local = shifted_points[:, 0] * cos_a - shifted_points[:, 1] * sin_a
        Y_local = shifted_points[:, 0] * sin_a + shifted_points[:, 1] * cos_a
        
        mask_x = np.abs(X_local) <= (width / 2)
        mask_y = np.abs(Y_local) <= (length / 2)
        
        final_mask = (mask_x & mask_y).reshape(self.mesh.nodes_X.shape)
        return final_mask & self.mesh.active_mask

    def apply_crane_rotation(self, track_L, track_W, gauge, chassis_angle_deg, load_L, load_R):
        """
        Đặt tải lên lưới với góc xoay chassis_angle.
        Hàm này được Solver Engine gọi để xác định vị trí đặt lò xo.
        """
        angle_rad = np.radians(chassis_angle_deg)
        
        # Ma trận xoay 2D
        cos_a, sin_a = np.cos(angle_rad), np.sin(angle_rad)
        
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
        
        # Tính áp lực sơ bộ (kN/m2) - Lưu ý: Solver sẽ tính lại áp lực thực tế sau.
        # Giá trị này chủ yếu để Solver xác định vị trí (Nodes) nào chịu tải.
        if area > 0:
            self.load_matrix[mask_left] = (load_L * 10) / area
            self.load_matrix[mask_right] = (load_R * 10) / area
            
        return self.load_matrix