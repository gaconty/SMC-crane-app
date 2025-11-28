import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.path import Path

# IMPORT MODULES
from unified_data import get_crane_options, get_processed_specs, get_valid_boom_lengths
from crane_physics import AdvancedCranePhysics
from mesh_engine import AdvancedMeshGenerator
from solver_engine import SoilStructureSolver

# CẤU HÌNH TRANG
st.set_page_config(page_title="SMC Crane Planner", layout="wide", page_icon="🏗️")

# --- STYLE COLORS ---
COLOR_BG_APP = '#ffffff'
COLOR_TEXT_MAIN = '#1e293b' # Slate 800
COLOR_TEXT_SEC = '#64748b'  # Slate 500
COLOR_ACCENT = '#0284c7'    # Sky 600
COLOR_SAFE = '#16a34a'      # Green 600
COLOR_DANGER = '#dc2626'    # Red 600

# --- CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp {{ background-color: #f8fafc; font-family: 'Roboto', sans-serif; color: {COLOR_TEXT_MAIN}; }}
    
    div[data-testid="metric-container"] {{
        background-color: white; border: 1px solid #e2e8f0; border-radius: 6px;
        padding: 10px 15px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    div[data-testid="metric-container"] label {{ font-size: 0.75rem; font-weight: 600; color: #64748b; }}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {{ font-size: 1.5rem; font-weight: 700; color: #0f172a; }}
    
    .info-panel {{
        background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); height: 100%;
    }}
    .panel-title {{
        font-size: 0.9rem; font-weight: 700; color: #334155; text-transform: uppercase;
        border-bottom: 2px solid #f1f5f9; padding-bottom: 8px; margin-bottom: 12px;
    }}
    .track-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9rem; }}
    .track-label {{ color: #64748b; font-weight: 500; }}
    .track-val {{ color: #0f172a; font-weight: 700; font-family: 'Roboto Mono', monospace; }}
    
    .badge-mat {{
        background: #fef3c7; color: #b45309; padding: 2px 6px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 700; border: 1px solid #fcd34d;
    }}
    
    .slew-container {{
        display: flex; align-items: center; justify-content: space-between;
        background: white; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;
    }}
</style>
""", unsafe_allow_html=True)

G_CONST = 9.81 

# --- HÀM VẼ PRO (CAD STYLE + CLIPPING MASK FIX) ---

def draw_pressure_profile_visual(specs, sol_res, mat_config, limit_p, mesh_obj=None, slew_angle=0):
    """
    Vẽ bản đồ áp lực.
    Fix: Clipping Mask cho Heatmap (không bị lem), Carbody Layering.
    """
    # CAD Colors
    C_STEEL = '#94a3b8'      
    C_TRACK_OUTLINE = '#334155' 
    C_MAT = '#f1f5f9'        
    C_MAT_BORDER = '#94a3b8' 
    C_DIM_LINE = '#64748b'   
    
    cmap = LinearSegmentedColormap.from_list("eng_grad", ["#ffffff", "#60a5fa", "#facc15", "#ef4444"])
    norm = Normalize(vmin=0, vmax=limit_p * 1.1)

    # Lấy thông số
    gauge = specs['track_gauge']
    trk_W = specs['track_W']
    trk_L = specs['track_L']
    
    if mat_config['use_left']: L_L, W_L, is_mat_L = mat_config['L_left'], mat_config['W_left'], True
    else: L_L, W_L, is_mat_L = trk_L, trk_W, False

    if mat_config['use_right']: L_R, W_R, is_mat_R = mat_config['L_right'], mat_config['W_right'], True
    else: L_R, W_R, is_mat_R = trk_L, trk_W, False

    # --- SETUP FIGURE ---
    max_W = max(W_L, W_R, trk_W)
    limit_x = gauge/2 + max_W + 2.5
    limit_y = max(L_L, L_R)/2 + 2.5
    
    ratio = limit_x / limit_y
    fig_h = 8; fig_w = fig_h * ratio
    
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), facecolor='white')
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_xlim(-limit_x, limit_x); ax.set_ylim(-limit_y, limit_y)

    # --- HELPERS ---
    def draw_dim_arrow(p1, p2, text, offset=0, color=C_DIM_LINE):
        x1, y1 = p1; x2, y2 = p2
        ax.plot([x1, x1], [y1, y1+offset], color=color, lw=0.5, alpha=0.5)
        ax.plot([x2, x2], [y2, y2+offset], color=color, lw=0.5, alpha=0.5)
        ax.annotate("", xy=(x1, y1+offset), xytext=(x2, y2+offset),
                    arrowprops=dict(arrowstyle='<->', color=color, lw=1.0, shrinkA=0, shrinkB=0))
        mid_x, mid_y = (x1+x2)/2, y1+offset
        bbox = dict(facecolor='white', edgecolor='none', pad=1, alpha=0.8)
        is_vert = abs(x1-x2) < 0.1
        rot = 90 if is_vert else 0
        va = 'center' if is_vert else 'bottom'
        ha = 'right' if is_vert else 'center'
        txt_off = 0.1 if not is_vert else -0.1
        ax.text(mid_x, mid_y + (0 if is_vert else txt_off), text, 
                color=color, fontsize=8, rotation=rot, ha=ha, va=va, fontweight='bold', bbox=bbox)

    # --- 1. VẼ CỤM CHÂN (TRACK + MAT) ---
    def draw_foot(center_x, w_mat, l_mat, has_mat):
        load = 0; eff_len = 0; eff_pct = 0
        
        # Tọa độ chính xác của hình chữ nhật cần clipping
        x_min_clip, y_min_clip = center_x - w_mat/2, -l_mat/2
        
        # Tạo Clipping Path
        clip_rect = patches.Rectangle((x_min_clip, y_min_clip), w_mat, l_mat, 
                                    transform=ax.transData, fill=False, visible=False)
        ax.add_patch(clip_rect)

        # A. TẤM LÓT (Nền dưới cùng)
        if has_mat:
            rect = patches.Rectangle((x_min_clip, y_min_clip), w_mat, l_mat,
                                   facecolor='#f8fafc', edgecolor='#cbd5e1', lw=1, hatch='///', alpha=0.5, zorder=1)
            ax.add_patch(rect)
            rect_border = patches.Rectangle((x_min_clip, y_min_clip), w_mat, l_mat,
                                          facecolor='none', edgecolor='#94a3b8', lw=1, zorder=1)
            ax.add_patch(rect_border)

        # B. HEATMAP (Dùng pcolormesh và cắt chính xác)
        if mesh_obj:
            X_coords = mesh_obj.nodes_X[0, :]
            Y_coords = mesh_obj.nodes_Y[:, 0]
            
            # Tính toán chỉ số lưới để lấy vùng áp lực
            def find_nearest_idx(arr, val):
                return np.argmin(np.abs(arr - val))

            idx_x_min = find_nearest_idx(X_coords, x_min_clip)
            idx_x_max = find_nearest_idx(X_coords, x_min_clip + w_mat)
            idx_y_min = find_nearest_idx(Y_coords, y_min_clip)
            idx_y_max = find_nearest_idx(Y_coords, y_min_clip + l_mat)
            
            # Cắt ma trận Z (áp lực)
            Z_map = sol_res['pressure_map'][idx_y_min:idx_y_max, idx_x_min:idx_x_max] / G_CONST
            
            # Cắt tọa độ X và Y (cần N+1 điểm cho N ô lưới)
            X_pcolor = X_coords[idx_x_min:idx_x_max+1]
            Y_pcolor = Y_coords[idx_y_min:idx_y_max+1]
            
            # Đảm bảo kích thước Z khớp với X và Y
            if Z_map.shape[0] > 0 and Z_map.shape[1] > 0:
                ax.pcolormesh(X_pcolor, Y_pcolor, Z_map, 
                              cmap=cmap, norm=norm, shading='flat', zorder=2)
                
                # Tính tải trọng
                ps_all = sol_res['pressure_map'] / G_CONST
                load_mask = (mesh_obj.nodes_X >= X_pcolor[:-1].min()) & (mesh_obj.nodes_X <= X_pcolor[:-1].max()) & \
                            (mesh_obj.nodes_Y >= Y_pcolor[:-1].min()) & (mesh_obj.nodes_Y <= Y_pcolor[:-1].max()) & \
                            (mesh_obj.active_mask)
                load = np.sum(ps_all[load_mask]) * mesh_obj.dA
                
                # Tính hiệu quả tiếp xúc
                contact_nodes_mask = load_mask & (ps_all > 0.1)
                total_nodes = np.sum(load_mask)
                                     
                contact_area_nodes = np.sum(contact_nodes_mask)
                
                eff_pct = (contact_area_nodes / total_nodes * 100) if total_nodes > 0 else 0
                eff_len = (contact_area_nodes * mesh_obj.dA) / w_mat if w_mat > 0 else 0

        # C. XÍCH CẨU (Lớp trên cùng)
        ax.add_patch(patches.Rectangle((center_x - trk_W/2, -trk_L/2), trk_W, trk_L,
                                     facecolor='none', edgecolor=C_TRACK_OUTLINE, lw=2, zorder=10))
        n_pads = 12
        pad_step = trk_L / n_pads
        for y in np.arange(-trk_L/2, trk_L/2, pad_step):
            ax.plot([center_x - trk_W/2, center_x + trk_W/2], [y, y], color=C_TRACK_OUTLINE, lw=0.5, alpha=0.6, zorder=10)
        ax.plot(center_x, trk_L/2 + 0.2, '^', color=C_TRACK_OUTLINE, ms=6, zorder=10)
        ax.plot(center_x, -trk_L/2 - 0.2, 'v', color=C_TRACK_OUTLINE, ms=6, zorder=10)

        # D. KÍCH THƯỚC
        side = 1 if center_x > 0 else -1
        draw_dim_arrow((center_x + (w_mat/2 + 0.5)*side, -l_mat/2), 
                       (center_x + (w_mat/2 + 0.5)*side, l_mat/2), 
                       f"{l_mat}m", offset=0.2*side)
        draw_dim_arrow((center_x - w_mat/2, -limit_y + 0.8),
                       (center_x + w_mat/2, -limit_y + 0.8),
                       f"{w_mat}m", offset=-0.2)

        return load, eff_len, eff_pct

    # Vẽ Trái/Phải
    l_L, e_L, pct_L = draw_foot(-gauge/2, W_L, L_L, is_mat_L)
    l_R, e_R, pct_R = draw_foot(gauge/2, W_R, L_R, is_mat_R)

    # --- 2. VẼ THÂN MÁY (CARBODY) ---
    draw_dim_arrow((-gauge/2, limit_y - 0.8), (gauge/2, limit_y - 0.8), f"{gauge}m", offset=0.3)

    beam_h = 0.4
    ax.add_patch(patches.Rectangle((-gauge/2, -beam_h/2), gauge, beam_h, facecolor=C_STEEL, edgecolor='none', zorder=5))
    
    cb_w = gauge - trk_W - 1.0
    cb_h = cb_w * 0.8 
    if cb_h > trk_L * 0.6: cb_h = trk_L * 0.6
    
    rect_cb = patches.Rectangle((-cb_w/2, -cb_h/2), cb_w, cb_h, 
                              facecolor='#f1f5f9', edgecolor=C_STEEL, lw=2, zorder=6)
    ax.add_patch(rect_cb)
    ax.plot([-cb_w/2, cb_w/2], [-cb_h/2, cb_h/2], color=C_STEEL, lw=1, alpha=0.3, zorder=6)
    ax.plot([-cb_w/2, cb_w/2], [cb_h/2, -cb_h/2], color=C_STEEL, lw=1, alpha=0.3, zorder=6)

    r_slew = min(cb_w, cb_h) * 0.4
    ax.add_patch(patches.Circle((0,0), r_slew, facecolor='white', edgecolor=COLOR_ACCENT, lw=2, zorder=7))
    
    rad = np.radians(90 - slew_angle)
    arr_len = r_slew * 0.8
    ax.arrow(0, 0, arr_len*np.cos(rad), arr_len*np.sin(rad), 
             head_width=r_slew*0.3, head_length=r_slew*0.3, fc='#0f172a', ec='none', zorder=8)
    
    cg_sz = r_slew * 0.25
    ax.add_patch(patches.Wedge((0,0), cg_sz, 0, 90, fc='black', zorder=9))
    ax.add_patch(patches.Wedge((0,0), cg_sz, 180, 270, fc='black', zorder=9))
    ax.add_patch(patches.Circle((0,0), cg_sz, fill=False, ec='black', lw=1, zorder=9))

    ax.text(0, -limit_y + 1.5, f"SLEW: {slew_angle}°", ha='center', fontsize=10, fontweight='bold', 
            bbox=dict(facecolor='white', edgecolor='#e2e8f0', boxstyle='round,pad=0.3'))

    # --- 3. LEGEND ---
    cbar_w = gauge * 0.8; cbar_h = 0.3
    cbar_x = -cbar_w/2; cbar_y = limit_y - 2.0
    grad = np.linspace(0, 1, 256); grad = np.vstack((grad, grad))
    ax.imshow(grad, aspect='auto', cmap=cmap, extent=[cbar_x, cbar_x+cbar_w, cbar_y, cbar_y+cbar_h], zorder=10)
    ax.add_patch(patches.Rectangle((cbar_x, cbar_y), cbar_w, cbar_h, fill=False, edgecolor='#94a3b8', lw=0.5, zorder=11))
    
    ax.text(cbar_x, cbar_y+cbar_h+0.15, "0 t/m²", ha='center', fontsize=7, color='#64748b')
    ax.text(cbar_x+cbar_w, cbar_y+cbar_h+0.15, f"{limit_p*1.1:.1f}", ha='center', fontsize=7, color=COLOR_DANGER, fontweight='bold')
    ax.text(0, cbar_y+cbar_h+0.15, "GROUND PRESSURE", ha='center', fontsize=7, fontweight='bold', color='#334155')

    return fig, l_L, l_R, e_L, e_R, pct_L, pct_R

# --- HÀM VẼ POLAR PRO (Chi tiết hơn) ---
def draw_polar_chart_pro(angles, p_values, current_slew, limit_p=30.0):
    theta = np.radians(angles)
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'}, facecolor='white')
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    
    # Grid đậm và chi tiết hơn
    ax.grid(color='#cbd5e1', linestyle='-', linewidth=0.8, alpha=0.6)
    
    # Tự động điều chỉnh giới hạn R
    r_max = max(np.max(p_values), limit_p) * 1.15
    r_ticks = np.linspace(0, r_max, 5)[1:]
    ax.set_rticks(r_ticks)
    ax.set_yticklabels([f"{r:.1f}" for r in r_ticks], fontsize=7, color='#475569') # Thêm nhãn R
    
    # Safe Zone
    ax.plot(theta, p_values, color=COLOR_ACCENT, lw=2.5, zorder=3)
    ax.fill_between(theta, 0, p_values, color='#7dd3fc', alpha=0.8, zorder=2) # Tăng alpha
    
    # Limit Line
    ax.plot(np.linspace(0, 2*np.pi, 360), [limit_p]*360, linestyle='--', color=COLOR_DANGER, lw=2, zorder=4)
    
    # Danger Zone
    ax.fill_between(theta, limit_p, p_values, where=(p_values > limit_p), color='#fca5a5', alpha=0.9, zorder=3)

    # Current Slew
    cur_rad = np.radians(current_slew)
    cur_val = np.interp(current_slew, angles, p_values)
    ax.plot([cur_rad, cur_rad], [0, r_max], color='#334155', lw=2, zorder=10)
    st_col = COLOR_DANGER if cur_val > limit_p else COLOR_SAFE
    ax.plot(cur_rad, cur_val, 'o', color='white', markeredgecolor=st_col, markeredgewidth=3, ms=9, zorder=11)
    
    # Nhãn góc chi tiết hơn
    ax.set_xticks(np.radians(np.arange(0, 360, 30)))
    ax.set_xticklabels([f"{x}°" for x in np.arange(0, 360, 30)], fontsize=8, color='#475569', fontweight='bold')
    
    # Label cho trục R (Tấn/m2)
    ax.text(np.radians(0), r_max * 1.05, "(t/m²)", ha='center', va='bottom', color='#64748b', fontsize=8)
    
    return fig

@st.cache_data(show_spinner=False)
def calculate_polar_profile(specs, load_mass, boom_angle, soil_ks, mat_config):
    # Tăng số điểm quét từ 10 độ lên 5 độ để Polar mịn hơn
    mesh_gen = AdvancedMeshGenerator(mesh_size=0.1) 
    L_sim = specs['track_L']
    if mat_config['use_left']: L_sim = max(L_sim, mat_config['L_left'])
    if mat_config['use_right']: L_sim = max(L_sim, mat_config['L_right'])
    mesh_gen.create_rectangular_mesh(L_sim*2.2, specs['track_gauge']*2.2, default_Ks=soil_ks)
    solver = SoilStructureSolver(mesh_gen)
    physics_engine = AdvancedCranePhysics(specs)
    solve_specs = specs.copy()
    if mat_config['use_left'] or mat_config['use_right']:
        solve_specs['track_L'] = L_sim
        solve_specs['track_W'] = max(specs['track_W'], mat_config.get('W_left',0), mat_config.get('W_right',0))
    angles = np.arange(0, 360, 5) # 5 degree step
    p_max_values = []
    for ang in angles:
        phys_angle = 90 - ang
        phys_res = physics_engine.calculate_state(load_mass, boom_angle, phys_angle)
        sol_res, _ = solver.solve_equilibrium(solve_specs, phys_res, chassis_angle=0)
        val = sol_res['pressure_max'] / G_CONST if sol_res else 0
        p_max_values.append(val)
    angles = np.append(angles, 360)
    p_max_values = np.append(p_max_values, p_max_values[0])
    return angles, np.array(p_max_values)

# ==============================================================================
# MAIN UI LAYOUT
# ==============================================================================

with st.sidebar:
    st.markdown("### 🏗️ CẤU HÌNH CẨU")
    options, msg = get_crane_options()
    if not options: st.error(msg); st.stop()
    
    with st.expander("1. THIẾT BỊ", expanded=True):
        crane_id = st.selectbox("Model", list(options.keys()))
        cwt_name = st.selectbox("Đối trọng", options[crane_id])
        valid_lens = get_valid_boom_lengths(crane_id)
        boom_len = st.select_slider("Chiều dài Cần (m)", options=valid_lens) if valid_lens else st.number_input("Cần (m)", 60.0)

    with st.expander("2. ĐỊA HÌNH & TẤM LÓT", expanded=True):
        c1, c2 = st.columns(2)
        slope_x = c1.number_input("Dốc Dọc (%)", -5.0, 5.0, 0.0, step=0.1)
        slope_y = c2.number_input("Dốc Ngang (%)", -5.0, 5.0, 0.0, step=0.1)
        
        st.markdown("---")
        use_mats = st.checkbox("Sử dụng tấm lót (Mats)", value=True)
        mat_config = {'use_left': False, 'L_left': 6.0, 'W_left': 2.0, 
                      'use_right': False, 'L_right': 6.0, 'W_right': 2.0}
        
        if use_mats:
            c_mat_l, c_mat_r = st.columns(2)
            with c_mat_l:
                if st.checkbox("Lót Trái", True):
                    mat_config['use_left'] = True
                    mat_config['L_left'] = st.number_input("L Trái (m)", value=6.0)
                    mat_config['W_left'] = st.number_input("W Trái (m)", value=2.0)
            with c_mat_r:
                if st.checkbox("Lót Phải", True):
                    mat_config['use_right'] = True
                    mat_config['L_right'] = st.number_input("L Phải (m)", value=6.0)
                    mat_config['W_right'] = st.number_input("W Phải (m)", value=2.0)
        
        limit_pressure = st.number_input("P-Allow (t/m²)", value=30.0)
        soil_ks = 30000

    st.markdown("### 📦 TẢI TRỌNG")
    load_mass = st.number_input("Khối lượng Hàng (Tấn)", value=80.0)
    radius = st.number_input("Bán kính (m)", value=12.0)
    
    # [NEW] SLEW INTERFACE (Slider + Circle Visual)
    st.markdown("---")
    st.markdown("**GÓC QUAY (Slew Angle)**")
    
    col_sl_1, col_sl_2 = st.columns([2, 1])
    
    with col_sl_1:
        # Slider interaction
        slew_angle = st.slider("Góc (Độ)", 0, 360, 45)
    
    with col_sl_2:
        # Small visual feedback
        fig_mini, ax_mini = plt.subplots(figsize=(1.2, 1.2), facecolor='#f8fafc')
        ax_mini.set_aspect('equal')
        ax_mini.axis('off')
        ax_mini.add_patch(patches.Circle((0,0), 1, fill=False, edgecolor='#64748b', lw=1.5))
        rad_mini = np.radians(90 - slew_angle)
        ax_mini.arrow(0, 0, 0.8*np.cos(rad_mini), 0.8*np.sin(rad_mini), 
                     head_width=0.25, head_length=0.2, fc='#0284c7', ec='#0284c7', lw=1.5)
        ax_mini.add_patch(patches.Rectangle((-0.3, -0.5), 0.6, 1.0, fill=False, edgecolor='#94a3b8', lw=0.8, linestyle='--'))
        st.pyplot(fig_mini, use_container_width=False)

# PROCESS DATA
specs, _ = get_processed_specs(crane_id, cwt_name, boom_len)
specs['slope_grade_x_pct'] = slope_x
specs['slope_roll_y_pct'] = slope_y

physics_engine = AdvancedCranePhysics(specs)
reach = min(radius - specs['pivot_x'], boom_len * 0.99)
boom_angle = np.degrees(np.arccos(reach/boom_len))
phys_res = physics_engine.calculate_state(load_mass, boom_angle, 90 - slew_angle)

mesh_gen = AdvancedMeshGenerator(mesh_size=0.05)
solve_specs = specs.copy()
sim_L = specs['track_L']
if mat_config['use_left'] or mat_config['use_right']:
    max_L_mat = max(mat_config['L_left'] if mat_config['use_left'] else 0,
                    mat_config['L_right'] if mat_config['use_right'] else 0)
    sim_L = max(sim_L, max_L_mat)
    if mat_config['use_left']: 
        solve_specs['track_L'] = mat_config['L_left'] 
        solve_specs['track_W'] = mat_config['W_left']

mesh_gen.create_rectangular_mesh(sim_L*2.5, specs['track_gauge']*2.5, default_Ks=soil_ks)
solver = SoilStructureSolver(mesh_gen)
sol_res, err = solver.solve_equilibrium(solve_specs, phys_res)
if err: st.error(err); st.stop()

# DASHBOARD HEADER
p_max = sol_res['pressure_max'] / G_CONST
sliding_force = np.sqrt(phys_res['Fx_slide_ton']**2 + phys_res['Fy_slide_ton']**2)
sf_slide = (phys_res['V_total_ton'] * 0.3) / (sliding_force + 1e-3)
sf_bearing = limit_pressure / p_max # Hệ số an toàn chịu tải nền

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1: st.metric("ÁP LỰC MAX", f"{p_max:.2f} t/m²", delta=f"{limit_pressure-p_max:.1f} dư", delta_color="normal" if p_max < limit_pressure else "inverse")
with k2: st.metric("TỔNG TẢI", f"{phys_res['V_total_ton']:.1f} T")
with k3: st.metric("LỰC TRƯỢT", f"{sliding_force:.1f} T")
with k4: st.metric("MÔ-MEN", f"{phys_res['Mz_yaw_Tm']:.1f} Tm")
with k5: st.metric("HS TRƯỢT", f"{sf_slide:.2f}", delta="Trượt" if sf_slide>1.2 else "Nguy hiểm", delta_color="normal" if sf_slide>1.2 else "inverse")
with k6: st.metric("HS NỀN", f"{sf_bearing:.2f}", delta="Đủ tải" if sf_bearing>1.0 else "Sụt lún", delta_color="normal" if sf_bearing>1.0 else "inverse")

st.markdown("---")

# DASHBOARD BODY
col_main, col_side = st.columns([2.5, 1])

with col_main:
    st.markdown("#### 🗺️ BẢN ĐỒ ÁP LỰC CHI TIẾT")
    fig_map, lL, lR, eL, eR, pct_L, pct_R = draw_pressure_profile_visual(specs, sol_res, mat_config, limit_pressure, mesh_gen, slew_angle)
    st.pyplot(fig_map, width='stretch')

with col_side:
    st.markdown("#### 📊 THÔNG SỐ CHI TIẾT")
    
    # Card Left
    st.markdown(f"""
    <div class="info-panel">
        <div class="panel-title">LEFT TRACK (Xích Trái) {'<span class="badge-mat">MATS</span>' if mat_config['use_left'] else ''}</div>
        <div class="track-row"><span class="track-label">Tải trọng:</span> <span class="track-val">{lL:.1f} T</span></div>
        <div class="track-row"><span class="track-label">Hiệu quả:</span> <span class="track-val">{pct_L:.0f}%</span></div>
        <div class="track-row"><span class="track-label">Chiều dài ép:</span> <span class="track-val">{eL:.2f} m</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
    
    # Card Right
    st.markdown(f"""
    <div class="info-panel">
        <div class="panel-title">RIGHT TRACK (Xích Phải) {'<span class="badge-mat">MATS</span>' if mat_config['use_right'] else ''}</div>
        <div class="track-row"><span class="track-label">Tải trọng:</span> <span class="track-val">{lR:.1f} T</span></div>
        <div class="track-row"><span class="track-label">Hiệu quả:</span> <span class="track-val">{pct_R:.0f}%</span></div>
        <div class="track-row"><span class="track-label">Chiều dài ép:</span> <span class="track-val">{eR:.2f} m</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    st.markdown("#### 🧭 ỔN ĐỊNH 360°")
    
    angles, vals = calculate_polar_profile(specs, load_mass, boom_angle, soil_ks, mat_config)
    fig_polar = draw_polar_chart_pro(angles, vals, slew_angle, limit_pressure)

    st.pyplot(fig_polar, width='stretch')
