import numpy as np

class AdvancedCranePhysics:
    def __init__(self, specs):
        """
        Khởi tạo Physics Engine.
        Nhận dữ liệu 'specs' đã được xử lý bởi unified_data (bao gồm logic lắp ghép module).
        """
        self.specs = specs
        self.g = 9.81 # Gia tốc trọng trường
        
        # 1. Thông số Cần (Boom)
        self.boom_len = specs.get('boom_len', 0.0)
        self.boom_mass = specs.get('boom_mass', 0.0)
        
        # [QUAN TRỌNG] Lấy trọng tâm thực tế đã tính từ các module lắp ghép
        # Nếu dữ liệu cũ không có key này, fallback về 50% chiều dài
        self.boom_cg_dist = specs.get('boom_cg_radius', self.boom_len * 0.5)
        
        pivot_x = specs.get('pivot_x', 0.0)
        pivot_z = specs.get('pivot_z', 0.0)
        self.boom_pivot = np.array([pivot_x, 0.0, pivot_z]) 
        
        # 2. Thân trên (Upper)
        self.upper_cg_local = np.array([-0.5, 0.0, 1.5]) # Giả định CG thân máy nằm lùi nhẹ
        self.upper_mass = specs.get('upper_mass', 0.0)
        
        # 3. Đối trọng (CWT)
        cwt_r = specs.get('cwt_radius', 0.0)
        # CWT nằm ở phía sau (x âm), cao hơn sàn máy một chút
        self.cwt_cg_local = np.array([-abs(cwt_r), 0.0, 1.2]) 
        self.cwt_mass = specs.get('cwt_mass', 0.0)
        
        # 4. Gầm xích (Carbody)
        self.carbody_mass = specs.get('carbody_mass', 0.0)
        
        # 5. Thông số khác
        self.gauge = specs.get('track_gauge', 6.0)
        self.H_Aframe = specs.get('A_frame_h', 3.0)

    def _get_rotation_matrix_Z(self, angle_deg):
        """Ma trận xoay quanh trục Z (Slew Rotation)"""
        rad = np.radians(angle_deg)
        c, s = np.cos(rad), np.sin(rad)
        return np.array([[c, -s, 0], [s,  c, 0], [0,  0, 1]])

    def calculate_state(self, load_mass, boom_angle_deg, slew_angle_deg):
        """
        Tính toán trạng thái cân bằng tĩnh (Static Equilibrium).
        Input:
            - load_mass: Tải trọng hàng (Tấn)
            - boom_angle: Góc nâng cần (Độ)
            - slew_angle: Góc quay toa (Độ)
        Output: Dictionary chứa tổng tải và các thành phần Moment.
        """
        # 1. TÍNH TOÁN TRONG HỆ TỌA ĐỘ CẦN (LOCAL BOOM FRAME)
        theta_rad = np.radians(boom_angle_deg)
        cos_t, sin_t = np.cos(theta_rad), np.sin(theta_rad)
        
        # Vector chỉ hướng của cần (Unit vector)
        boom_vec = np.array([cos_t, 0.0, sin_t])
        
        # A. Vị trí Đỉnh cần (Boom Tip) -> Dùng để xác định vị trí Hàng & Bán kính
        tip_local_vec = boom_vec * self.boom_len
        
        # B. Vị trí Trọng tâm cần (Boom CG) -> Dùng để tính Moment bản thân cần
        # Đây là điểm nâng cấp: Dùng boom_cg_dist thực tế thay vì chia đôi
        boom_cg_vec = boom_vec * self.boom_cg_dist
        
        # 2. CHUYỂN SANG HỆ TỌA ĐỘ THÂN MÁY (LOCAL BODY FRAME)
        # Cộng thêm offset của chốt chân cần (Pivot)
        tip_body = self.boom_pivot + tip_local_vec
        boom_cg_body = self.boom_pivot + boom_cg_vec
        
        # Tính bán kính làm việc (Radius) từ tâm quay
        geom_radius = tip_body[0] # Chỉ lấy tọa độ X
        
        # 3. XOAY TOÀN BỘ SANG HỆ TỌA ĐỘ ĐẤT (WORLD FRAME)
        # Xoay theo góc Slew
        Rot_Z = self._get_rotation_matrix_Z(slew_angle_deg)
        
        # Tọa độ các thành phần trong không gian 3D thực tế
        upper_world = Rot_Z @ self.upper_cg_local
        cwt_world   = Rot_Z @ self.cwt_cg_local
        boom_world  = Rot_Z @ boom_cg_body
        load_world  = Rot_Z @ tip_body # Hàng treo thẳng đứng dưới đỉnh cần
        
        # 4. TÍNH TOÁN MOMENT LẬT (TIPPING MOMENTS)
        # Quy ước: Moment tính quanh gốc tọa độ (0,0,0) tại tâm quay máy trên mặt đất.
        # Mx (Roll): Quay quanh trục X -> Do lực tại Y gây ra.
        # My (Pitch): Quay quanh trục Y -> Do lực tại X gây ra.
        
        def calc_moments(mass, pos_vec):
            # Cánh tay đòn
            rx, ry = pos_vec[0], pos_vec[1]
            
            # Moment = Force * Distance
            # Fz (Trọng lực) hướng xuống (-).
            # Mx = y * Fz. My = -x * Fz.
            # Tuy nhiên, để đơn giản cho Solver (thường quy ước dương là gây lún),
            # ta tính Moment gây lật (Overturning Moment) theo độ lớn Tấn.m
            
            # Moment xoay quanh trục X (Roll): Lực tác dụng ở Y càng lớn -> Moment càng lớn
            mx = mass * ry 
            
            # Moment xoay quanh trục Y (Pitch): Lực tác dụng ở X (phía trước) -> Chúi đầu
            # Dấu (-): X dương (trước mặt) gây moment chúi (âm) hoặc ngược lại tùy quy ước Solver.
            # Solver cũ dùng: My_react = sum(F * -X).
            # Nên ở đây ta giữ quy ước: X dương -> My âm (chúi). X âm (đối trọng) -> My dương (ngửa).
            my = mass * (-rx)
            
            return mx, my

        Mx_u, My_u = calc_moments(self.upper_mass, upper_world)
        Mx_c, My_c = calc_moments(self.cwt_mass, cwt_world)
        Mx_b, My_b = calc_moments(self.boom_mass, boom_world)
        Mx_l, My_l = calc_moments(load_mass, load_world)
        
        # Tổng hợp Moment
        Mx_net = Mx_u + Mx_c + Mx_b + Mx_l
        My_net = My_u + My_c + My_b + My_l
        
        # 5. TỔNG TẢI TRỌNG ĐÈ XUỐNG (VERTICAL LOAD)
        # Bao gồm cả Carbody (dù carbody không tạo moment lật vì nằm tại tâm hoặc đối xứng, nhưng góp phần vào V_total để nén đất)
        V_total = self.upper_mass + self.cwt_mass + self.carbody_mass + self.boom_mass + load_mass
        
        return {
            "V_total_ton": V_total, 
            "Mx_roll_Tm": Mx_net,     
            "My_pitch_Tm": My_net,
            "geom_radius": geom_radius,
            # Trả thêm tọa độ đỉnh cần để UI vẽ nếu cần
            "tip_pos_world": (load_world[0], load_world[1]) 
        }