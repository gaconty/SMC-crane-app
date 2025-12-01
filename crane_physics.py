import numpy as np
from scipy.spatial.transform import Rotation as R

class AdvancedCranePhysics:
    def __init__(self, specs):
        self.specs = specs
        self.g_mag = 9.81
        
        # Extract slope if present, else 0
        slope_y_pct = specs.get('slope_y_pct', 0.0)
        angle_x = specs.get('angle_x', 0.0) # Assuming angle_x might be needed too
        
        angle_y = np.arctan(slope_y_pct / 100.0)
        
        r_x = R.from_euler('x', angle_y)
        r_y = R.from_euler('y', -angle_x)
        self.R_slope = r_y * r_x
        
        g_global = np.array([0.0, 0.0, -self.g_mag])
        self.g_vec = self.R_slope.inv().apply(g_global)
        
        # 2. Khởi tạo các Vector vị trí tĩnh
        self.pos_carbody = np.array([0.0, 0.0, specs.get('carbody_cg_z', 0.8)])
        self.pos_upper = np.array([-0.5, 0.0, specs.get('upper_cg_z', 1.5)])
        self.pos_cwt = np.array([-specs['cwt_radius'], 0.0, specs.get('cwt_z', 1.2)])
        self.pos_pivot = np.array([specs['pivot_x'], 0.0, specs['pivot_z']])
        
        self.boom_len = specs['boom_len']
        self.boom_cg_dist = specs['boom_cg_radius']

    def _get_rotation_matrix_Z(self, angle_deg):
        rad = np.radians(angle_deg)
        c, s = np.cos(rad), np.sin(rad)
        return np.array([
            [c, -s, 0],
            [s,  c, 0],
            [0,  0, 1]
        ])

    def _calc_wrench(self, mass_ton, pos_vec):
        """
        Output:
         - Force Vector (kN): [Fx, Fy, Fz] (Vì mass_ton * 9.81 ~ kN)
         - Moment Vector (kNm): [Mx, My, Mz]
        """
        force_vec = mass_ton * self.g_vec 
        moment_vec = np.cross(pos_vec, force_vec)
        return force_vec, moment_vec

    def calculate_state(self, load_mass, boom_angle_deg, slew_angle_deg, jib_length=0.0, jib_offset_deg=0.0, jib_mass=0.0):
        # 1. Kinematics
        theta = np.radians(boom_angle_deg)
        boom_dir = np.array([np.cos(theta), 0.0, np.sin(theta)])
        
        p_boom_cg_local = self.pos_pivot + (boom_dir * self.boom_cg_dist)
        p_tip_local = self.pos_pivot + (boom_dir * self.boom_len)
        
        # Jib Logic
        if jib_length > 0:
            # Jib angle relative to ground = Boom angle - Jib offset
            jib_angle_deg = boom_angle_deg - jib_offset_deg
            theta_jib = np.radians(jib_angle_deg)
            jib_dir = np.array([np.cos(theta_jib), 0.0, np.sin(theta_jib)])
            
            # Jib CG (Assume middle)
            p_jib_cg_local = p_tip_local + (jib_dir * (jib_length / 2.0))
            # New Tip (Hook Point)
            p_hook_local = p_tip_local + (jib_dir * jib_length)
            
            # Add Jib to bodies later
            has_jib = True
        else:
            p_hook_local = p_tip_local
            has_jib = False
            
        p_load_local = p_hook_local
        
        # 2. Slew Rotation
        Rot_Z = self._get_rotation_matrix_Z(slew_angle_deg)
        
        p_upper_world = Rot_Z @ self.pos_upper
        p_cwt_world   = Rot_Z @ self.pos_cwt
        p_boom_world  = Rot_Z @ p_boom_cg_local
        p_load_world  = Rot_Z @ p_load_local
        p_carbody_world = self.pos_carbody
        
        # 3. Tính Wrench (kN và kNm)
        forces = []
        moments = []
        
        bodies = [
            (self.specs['carbody_mass'], p_carbody_world),
            (self.specs.get('carbody_cwt_mass', 0.0), p_carbody_world), # Carbody Counterweight
            (self.specs['upper_mass'],   p_upper_world),
            (self.specs['cwt_mass'],     p_cwt_world),
            (self.specs['boom_mass'],    p_boom_world),
            (load_mass,                  p_load_world)
        ]
        
        if has_jib:
            p_jib_world = Rot_Z @ p_jib_cg_local
            bodies.append((jib_mass, p_jib_world))
        
        for m, p in bodies:
            f, m_vec = self._calc_wrench(m, p)
            forces.append(f)
            moments.append(m_vec)
            
        # 4. Tổng hợp (kN, kNm)
        F_total_kN = np.sum(forces, axis=0) 
        M_total_kNm = np.sum(moments, axis=0) 
        
        # 5. [FIX UNIT] Chuyển đổi về Tấn và Tấn.m
        # F_total[2] là lực dọc trục Z (kN). Chia g để ra Tấn trọng lượng.
        V_load_ton = abs(F_total_kN[2]) / self.g_mag
        
        # Moment (kNm) chia g để ra Tấn.m (Tonne-force meter)
        Mx_Tm = M_total_kNm[0] / self.g_mag
        My_Tm = M_total_kNm[1] / self.g_mag
        Mz_Tm = M_total_kNm[2] / self.g_mag
        
        Fx_ton = F_total_kN[0] / self.g_mag
        Fy_ton = F_total_kN[1] / self.g_mag
        
        # Calculate Tip Height (Z coordinate of hook)
        tip_height = p_load_world[2]

        return {
            "V_total_ton": V_load_ton, # Đã chuẩn đơn vị Tấn
            "Mx_roll_Tm": Mx_Tm,       # Đã chuẩn đơn vị Tm
            "My_pitch_Tm": My_Tm,
            "Mz_yaw_Tm": Mz_Tm,
            "Fx_slide_ton": Fx_ton,
            "Fy_slide_ton": Fy_ton,
            "geom_radius": np.sqrt(p_load_world[0]**2 + p_load_world[1]**2),
            "tip_pos_world": (p_load_world[0], p_load_world[1]),
            "tip_height": tip_height
        }