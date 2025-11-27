import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.cm as cm
from matplotlib.colors import Normalize, LinearSegmentedColormap

# IMPORT MODULES
from unified_data import get_crane_options, get_processed_specs, get_valid_boom_lengths
from crane_physics import AdvancedCranePhysics
from mesh_engine import AdvancedMeshGenerator
from solver_engine import SoilStructureSolver

# CẤU HÌNH TRANG
st.set_page_config(page_title="SMC Crane Analysis", layout="wide", page_icon="🏗️")

# --- THEME COLORS ---
COLOR_BG = '#F8FAFC'       
COLOR_CARD = '#FFFFFF'     
COLOR_TEXT_MAIN = '#0F172A' 
COLOR_TEXT_SEC = '#475569'  
COLOR_ACCENT = '#0369A1'    

COLOR_DATA_LINE = '#0284C7' 
COLOR_DATA_FILL = '#BAE6FD' 
COLOR_LIMIT = '#DC2626'     
COLOR_MARKER = '#0C4A6E'    
COLOR_GRID = '#334155'      

# --- CSS STYLING ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    .stApp {{ background-color: {COLOR_BG}; font-family: 'Inter', sans-serif; }}
    h1, h2, h3, h4, h5 {{ color: {COLOR_TEXT_MAIN} !important; font-family: 'Inter', sans-serif; }}
    p, label, span {{ color: {COLOR_TEXT_SEC} !important; }}
    
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        background-color: {COLOR_CARD};
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 20px;
    }}

    .header-title {{ 
        font-size: 1.1rem; 
        font-weight: 700; 
        color: {COLOR_TEXT_MAIN}; 
        margin-bottom: 15px; 
        display: flex; 
        align-items: center; 
        gap: 8px; 
    }}
    
    .kpi-box {{
        text-align: center;
        padding: 15px;
        border-radius: 8px;
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }}
    .kpi-label {{ font-size: 0.85rem; color: {COLOR_TEXT_SEC}; font-weight: 600; text-transform: uppercase; }}
    .kpi-value {{ font-size: 1.6rem; color: {COLOR_TEXT_MAIN}; font-weight: 800; margin-top: 5px; }}
    
    .status-badge {{
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }}
    .status-safe {{ background-color: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }}
    .status-danger {{ background-color: #FEE2E2; color: #991B1B; border: 1px solid #FCA5A5; }}

    div[data-testid="stNumberInput"] {{ border: 1px solid #CBD5E1; border-radius: 8px; }}
    div[data-testid="stNumberInput"] input {{ color: {COLOR_TEXT_MAIN}; font-weight: 600; }}
    div[role="slider"] {{ background-color: {COLOR_DATA_LINE} !important; border-color: {COLOR_DATA_LINE} !important; }}
    
    .report-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9rem; }}
    .report-table td {{ padding: 10px 12px; border-bottom: 1px solid #E2E8F0; color: {COLOR_TEXT_MAIN}; }}
    .report-table td:first-child {{ font-weight: 600; color: {COLOR_TEXT_SEC}; width: 40%; background-color: #F8FAFC; }}
</style>
""", unsafe_allow_html=True)

# --- LOGIC ---
G_CONST = 9.81 

@st.cache_data(show_spinner=False)
def calculate_polar_profile(specs, load_mass, boom_angle, soil_ks, mat_config):
    mesh_gen = AdvancedMeshGenerator(mesh_size=0.2) 
    
    max_L_sim = max(mat_config['L_left'] if mat_config['use_left'] else specs['track_L'],
                    mat_config['L_right'] if mat_config['use_right'] else specs['track_L'])
    max_dim = max(max_L_sim, specs['track_gauge']) * 2.5
    mesh_gen.create_rectangular_mesh(max_dim, max_dim, default_Ks=soil_ks)
    solver = SoilStructureSolver(mesh_gen)
    physics_engine = AdvancedCranePhysics(specs)

    specs_L = specs.copy()
    if mat_config['use_left']:
        specs_L['track_L'] = mat_config['L_left']
        specs_L['track_W'] = mat_config['W_left']
    specs_R = specs.copy()
    if mat_config['use_right']:
        specs_R['track_L'] = mat_config['L_right']
        specs_R['track_W'] = mat_config['W_right']

    angles = np.arange(0, 360, 10) 
    p_max_values = []
    
    for ang in angles:
        phys_angle = 90 - ang
        phys_res = physics_engine.calculate_state(load_mass, boom_angle, phys_angle)
        
        if phys_res['Mx_roll_Tm'] >= 0: current_specs = specs_R
        else: current_specs = specs_L
        
        sol_res, _ = solver.solve_equilibrium(current_specs, phys_res, chassis_angle=0)
        
        val = sol_res['pressure_max'] / G_CONST if sol_res else 0
        p_max_values.append(val)

    angles = np.append(angles, 360)
    p_max_values = np.append(p_max_values, p_max_values[0])
    return angles, np.array(p_max_values)

def draw_polar_chart_pro(angles, p_values, current_slew, limit_p=30.0):
    theta = np.radians(angles)
    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw={'projection': 'polar'}, facecolor='none')
    ax.set_facecolor('none') 
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    
    ax.grid(color=COLOR_GRID, linestyle='--', linewidth=1.0, alpha=0.6)
    
    ax.spines['polar'].set_visible(False)
    ax.set_xticks(np.radians(np.arange(0, 360, 30)))
    ax.set_xticklabels([f"{x}°" for x in np.arange(0, 360, 30)], color=COLOR_TEXT_SEC, fontsize=8, fontweight='bold')
    
    max_data = np.max(p_values)
    limit_view = max(max_data, limit_p) * 1.15
    if limit_view == 0: limit_view = 10
    ax.set_ylim(0, limit_view)
    
    yticks = np.linspace(0, limit_view, 5)[1:] 
    ax.set_yticks(yticks)
    ax.set_yticklabels([f"{int(y)}" for y in yticks], color=COLOR_TEXT_SEC, fontsize=7)
    ax.text(np.radians(0), limit_view*1.05, "(t/m²)", ha='center', va='bottom', color=COLOR_TEXT_SEC, fontsize=8)

    # --- OVERLOAD ZONES HIGHLIGHT ---
    theta_bar = theta[:-1]
    val_bar = p_values[:-1]
    overload_mask = val_bar > limit_p
    
    if np.any(overload_mask):
        width_rad = 2 * np.pi / len(theta_bar)
        ax.bar(theta_bar[overload_mask], 
               [limit_view] * np.sum(overload_mask), 
               width=width_rad, bottom=0, 
               color='#FEE2E2', alpha=0.8, edgecolor='none', zorder=1)
        ax.bar(theta_bar[overload_mask], 
               [limit_view*0.02] * np.sum(overload_mask), 
               width=width_rad, bottom=limit_view*0.98, 
               color=COLOR_LIMIT, alpha=1.0, edgecolor='none', zorder=1)

    # --- DATA LINES ---
    ax.plot(theta, p_values, color=COLOR_DATA_LINE, linewidth=3.5, zorder=5, alpha=1.0)
    ax.fill(theta, p_values, color=COLOR_DATA_FILL, alpha=0.6, zorder=2)
    
    theta_c = np.linspace(0, 2*np.pi, 100)
    ax.plot(theta_c, np.full_like(theta_c, limit_p), linestyle='--', color=COLOR_LIMIT, linewidth=2.0, alpha=0.9, label='Limit')
    
    cur_rad = np.radians(current_slew)
    cur_p = np.interp(current_slew, angles, p_values)
    ax.plot([cur_rad, cur_rad], [0, limit_view], color=COLOR_TEXT_MAIN, linewidth=1.5, zorder=15)
    
    status_color = COLOR_LIMIT if cur_p > limit_p else COLOR_DATA_LINE
    ax.plot(cur_rad, cur_p, 'o', ms=12, mfc='white', mec=status_color, mew=3.0, zorder=20)
    
    ax.text(0, -limit_view*0.2, f"{cur_p:.1f}", color=status_color, fontsize=24, fontweight='bold', ha='center')
    ax.text(0, -limit_view*0.35, "t/m²", color=COLOR_TEXT_SEC, fontsize=10, ha='center')
    return fig

def draw_ground_pressure_map_pro(specs, phys_res, sol_res, mesh_gen, slew_angle, mat_config):
    L_trk, W_trk = specs['track_L'], specs['track_W']
    gauge = specs['track_gauge']
    
    L_L = mat_config['L_left'] if mat_config['use_left'] else L_trk
    W_L = mat_config['W_left'] if mat_config['use_left'] else W_trk
    L_R = mat_config['L_right'] if mat_config['use_right'] else L_trk
    W_R = mat_config['W_right'] if mat_config['use_right'] else W_trk

    X_grid, Y_grid, P_grid = mesh_gen.nodes_X, mesh_gen.nodes_Y, sol_res['pressure_map']
    dA = mesh_gen.dA
    mask_L = (X_grid < -0.1) & (P_grid > 0.001)
    mask_R = (X_grid > 0.1) & (P_grid > 0.001)

    def analyze(mask, L_ref):
        if not np.any(mask): 
            return {'p_top': 0, 'p_bot': 0, 'y_top': 0, 'y_bot': 0, 'len_pct': 0, 'len_m': 0}
        y_act, p_act = Y_grid[mask], P_grid[mask]
        eff_len = np.max(y_act) - np.min(y_act)
        return {
            'p_top': p_act[np.argmax(y_act)], 'p_bot': p_act[np.argmin(y_act)],
            'y_top': np.max(y_act), 'y_bot': np.min(y_act),
            'len_m': eff_len,
            'len_pct': min((eff_len/L_ref)*100, 100)
        }

    dL, dR = analyze(mask_L, L_L), analyze(mask_R, L_R)
    RL, RR = np.sum(P_grid[X_grid < 0]) * dA, np.sum(P_grid[X_grid > 0]) * dA

    fig, ax = plt.subplots(figsize=(10, 10), facecolor='none')
    ax.set_facecolor('none')
    
    # 1. TẤM LÓT (Xóa text label)
    if mat_config['use_left']:
        xc = -gauge/2
        ax.add_patch(patches.Rectangle((xc - W_L/2, -L_L/2), W_L, L_L, facecolor='#F1F5F9', edgecolor='#94A3B8', ls='--', zorder=0))
    
    if mat_config['use_right']:
        xc = gauge/2
        ax.add_patch(patches.Rectangle((xc - W_R/2, -L_R/2), W_R, L_R, facecolor='#F1F5F9', edgecolor='#94A3B8', ls='--', zorder=0))

    # 2. XÍCH (Xóa text label)
    for xc in [-gauge/2, gauge/2]:
        ax.add_patch(patches.Rectangle((xc-W_trk/2, -L_trk/2), W_trk, L_trk, facecolor='#E2E8F0', edgecolor='#475569', zorder=1))
        for ys in np.linspace(-L_trk/2, L_trk/2, 18):
            ax.plot([xc-W_trk/2, xc+W_trk/2], [ys, ys], color='#94A3B8', lw=0.5, zorder=1)
        ax.plot(xc, L_trk/2 + 0.4, '^', color=COLOR_ACCENT, ms=8)

    # 3. ÁP LỰC
    p_max_disp = max(sol_res['pressure_max'], 1.0)
    scale = (max(W_L, W_R) * 2.5) / p_max_disp 
    norm = Normalize(vmin=0, vmax=p_max_disp)
    cmap = plt.get_cmap('RdYlBu_r')

    def draw_poly(xc, d, side, W_ref):
        if d['len_m'] < 0.1: return
        xe = xc - W_ref/2 if side == 'left' else xc + W_ref/2
        sgn = -1 if side == 'left' else 1
        w_t = max(d['p_top']*scale, 0.05)
        w_b = max(d['p_bot']*scale, 0.05)
        
        verts = [(xe, d['y_top']), (xe+w_t*sgn, d['y_top']), (xe+w_b*sgn, d['y_bot']), (xe, d['y_bot'])]
        
        color_top, color_bot = cmap(norm(d['p_top'])), cmap(norm(d['p_bot']))
        grad_cmap = LinearSegmentedColormap.from_list("custom", [color_bot, color_top])
        
        poly = patches.Polygon(verts, closed=True, zorder=2, transform=ax.transData)
        ax.add_patch(poly) 
        
        gradient = np.linspace(0, 1, 256).reshape(-1, 1)
        x_min, x_max = min(v[0] for v in verts), max(v[0] for v in verts)
        y_min, y_max = min(v[1] for v in verts), max(v[1] for v in verts)
        im = ax.imshow(gradient, aspect='auto', extent=(x_min, x_max, y_min, y_max), cmap=grad_cmap, zorder=2, alpha=0.85)
        im.set_clip_path(poly)
        ax.add_patch(patches.Polygon(verts, closed=True, edgecolor=color_top, facecolor='none', lw=0.8, zorder=3))

        bbox_props = dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7)
        txt_off = 0.6 * sgn
        align = 'right' if side == 'left' else 'left'
        
        if d['p_top'] > 0.1:
            ax.text(xe+w_t*sgn+txt_off, d['y_top'], f"{d['p_top']:.1f} t/m²", ha=align, va='center', fontsize=10, fontweight='bold', color=COLOR_TEXT_MAIN, bbox=bbox_props)
        if d['p_bot'] > 0.1:
            ax.text(xe+w_b*sgn+txt_off, d['y_bot'], f"{d['p_bot']:.1f} t/m²", ha=align, va='center', fontsize=10, fontweight='bold', color=COLOR_TEXT_MAIN, bbox=bbox_props)

    draw_poly(-gauge/2, dL, 'left', W_L)
    draw_poly(gauge/2, dR, 'right', W_R)

    # 4. DIMENSIONS
    dim_style = dict(arrowstyle='-|>', color='#64748B', lw=1.2)
    def draw_dim_v(x, y1, y2, t, side=1):
        off = 0.5 * side
        ax.annotate("", xy=(x, y1), xytext=(x+off, y1), arrowprops=dict(arrowstyle='-', color='#94A3B8', zorder=20))
        ax.annotate("", xy=(x, y2), xytext=(x+off, y2), arrowprops=dict(arrowstyle='-', color='#94A3B8', zorder=20))
        ax.annotate("", xy=(x+off, y1), xytext=(x+off, y2), arrowprops=dim_style)
        ax.annotate("", xy=(x+off, y2), xytext=(x+off, y1), arrowprops=dim_style)
        ax.text(x+off+0.2*side, (y1+y2)/2, t, rotation=90, va='center', ha='left' if side==1 else 'right', color=COLOR_TEXT_SEC, fontsize=9, fontweight='bold', bbox=dict(fc='white', ec='none', pad=1))
    
    def draw_dim_h(x1, x2, y, t):
        ax.annotate("", xy=(x1, y), xytext=(x2, y), arrowprops=dim_style)
        ax.annotate("", xy=(x2, y), xytext=(x1, y), arrowprops=dim_style)
        ax.text((x1+x2)/2, y+0.2, t, ha='center', va='bottom', color=COLOR_TEXT_SEC, fontsize=9, fontweight='bold')

    # Tính toán vị trí Dim
    vis_w_L = max(dL['p_top'], dL['p_bot']) * scale if dL['len_m'] > 0 else 0
    vis_w_R = max(dR['p_top'], dR['p_bot']) * scale if dR['len_m'] > 0 else 0
    
    offset_dim_L = W_L/2 + vis_w_L + 2.5
    offset_dim_R = W_R/2 + vis_w_R + 2.5
    
    draw_dim_v(-gauge/2 - offset_dim_L, -L_L/2, L_L/2, f"{L_L:.1f}m", side=-1)
    draw_dim_v(gauge/2 + offset_dim_R, -L_R/2, L_R/2, f"{L_R:.1f}m")

    draw_dim_h(-gauge/2 - W_L/2, -gauge/2 + W_L/2, L_L/2 + 0.5, f"{W_L:.1f}m")
    draw_dim_h(gauge/2 - W_R/2, gauge/2 + W_R/2, L_R/2 + 0.5, f"{W_R:.1f}m")
    draw_dim_h(-gauge/2, gauge/2, max(L_L, L_R)/2 + 1.5, f"Gauge {gauge:.2f}m")

    # 5. CHASSIS
    cw, ch = gauge - W_trk - 0.5, L_trk * 0.4
    ax.add_patch(patches.Rectangle((-cw/2, -ch/2), cw, ch, facecolor='#CBD5E1', zorder=0))
    ax.add_patch(patches.Circle((0,0), gauge*0.35, fill=False, edgecolor=COLOR_ACCENT, lw=3, zorder=3))
    
    if phys_res['V_total_ton'] > 0:
        cy, cx = phys_res['Mx_roll_Tm']/phys_res['V_total_ton'], -phys_res['My_pitch_Tm']/phys_res['V_total_ton']
        cx, cy = np.clip(cx, -gauge, gauge), np.clip(cy, -L_trk, L_trk)
        ax.plot([0, cx], [0, cy], color='#475569', lw=2, zorder=4)
        ax.plot(0, 0, 'o', ms=6, mfc='white', mec='#475569', mew=2, zorder=4)
        ax.add_patch(patches.Circle((cx, cy), W_trk * 0.35, fill=False, edgecolor='black', lw=1, zorder=6))

    # Dời text "Góc Quay"
    ax.text(0, -max(L_L, L_R, L_trk)/2 - 7.5, f"Góc Quay: {slew_angle:.1f}°", color=COLOR_TEXT_MAIN, fontsize=14, fontweight='bold', ha='center')

    # 6. INFO BOXES (FIX OVERLAP)
    def draw_info_box(x_pos, y_pos, title, load, eff_len, eff_pct):
        content = f"{title}\nLOAD: {load:.1f}T\nEFF LEN: {eff_len:.2f}m ({eff_pct:.0f}%)"
        ax.text(x_pos, y_pos, content, ha='center', va='top', 
                color=COLOR_TEXT_MAIN, fontsize=9, family='monospace', fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.4", fc="#F8FAFC", ec="#94A3B8", lw=1))

    box_y = -max(L_L, L_R, L_trk)/2 - 3.5
    
    # [FIX] Tính toán vị trí an toàn cho Box
    # Nếu gauge nhỏ hơn 6m, đẩy 2 box ra xa trung tâm để không đè nhau
    safe_dist = 7.0 # Khoảng cách tối thiểu giữa 2 tâm box (ước lượng)
    
    # Vị trí mặc định là tâm track (-gauge/2, gauge/2)
    # Nếu gauge < safe_dist, ta dùng vị trí cưỡng bức bên ngoài
    pos_L = min(-gauge/2, -safe_dist/2)
    pos_R = max(gauge/2, safe_dist/2)
    
    draw_info_box(pos_L, box_y, "LEFT TRACK", RL, dL['len_m'], dL['len_pct'])
    draw_info_box(pos_R, box_y, "RIGHT TRACK", RR, dR['len_m'], dR['len_pct'])

    # Tăng giới hạn khung hình
    lim_x = max(gauge/2, safe_dist/2) + max(offset_dim_L, offset_dim_R) + 2
    lim_y = max(L_L, L_R)/2 + 8 
    lim = max(lim_x, lim_y)
    
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.axis('off'); ax.set_aspect('equal')
    return fig, RL, RR, dL['len_pct'], dR['len_pct']

# ==============================================================================
# MAIN UI
# ==============================================================================

with st.sidebar:
    st.title("⚙️ CẤU HÌNH")
    st.markdown("---")
    options, msg = get_crane_options()
    if not options: st.error(msg); st.stop()
    
    with st.expander("1. Chọn Thiết Bị", expanded=True):
        crane_id = st.selectbox("Model", list(options.keys()))
        cwt_name = st.selectbox("Đối trọng", options[crane_id])
        
        valid_lens = get_valid_boom_lengths(crane_id)
        if valid_lens:
            boom_len = st.select_slider("Chiều dài Cần (m)", options=valid_lens, value=valid_lens[len(valid_lens)//2])
            st.caption(f"🧩 Cấu hình tự động: Gốc + Ngọn + Inserts ({boom_len}m)")
        else:
            st.warning("Không tìm thấy cấu hình Boom module. Dùng nhập liệu thủ công.")
            boom_len = st.number_input("Chiều dài Cần (m)", 20.0, 150.0, 60.0, step=3.0)

    with st.expander("2. Tấm Lót (Mats)", expanded=False):
        use_mats = st.checkbox("Kích hoạt")
        mat_config = {'use_left': False, 'L_left': 0, 'W_left': 0, 'use_right': False, 'L_right': 0, 'W_right': 0}
        if use_mats:
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Trái")
                if st.checkbox("Lót Trái", value=True):
                    mat_config['use_left'] = True
                    mat_config['L_left'] = st.number_input("L (m)", 1.0, 15.0, 8.0, key="LL")
                    mat_config['W_left'] = st.number_input("W (m)", 1.0, 5.0, 2.0, key="WL")
            with c2:
                st.caption("Phải")
                if st.checkbox("Lót Phải", value=True):
                    mat_config['use_right'] = True
                    mat_config['L_right'] = st.number_input("L (m)", 1.0, 15.0, 8.0, key="LR")
                    mat_config['W_right'] = st.number_input("W (m)", 1.0, 5.0, 2.0, key="WR")

    with st.expander("3. Địa chất", expanded=False):
        soil_ks = 30000 if st.radio("Đất", ["Tốt", "Yếu"]) == "Tốt" else 5000
        limit_pressure = st.number_input("P-Allow (t/m²)", 10.0, 100.0, 30.0)

st.markdown(f"<h2 style='text-align: center; margin-bottom: 30px;'>SMC GROUND PRESSURE ANALYSIS</h2>", unsafe_allow_html=True)

# CARDS & INPUTS
c1, c2, c3 = st.columns([1, 1, 1.5])
with c1:
    with st.container(border=True):
        st.markdown(f"<div class='header-title'>📦 Tải trọng (Tấn)</div>", unsafe_allow_html=True)
        load_mass = st.number_input("Load", 0.0, 600.0, 80.0, label_visibility="collapsed")
with c2:
    with st.container(border=True):
        st.markdown(f"<div class='header-title'>📏 Bán kính (m)</div>", unsafe_allow_html=True)
        radius = st.number_input("Radius", 5.0, 100.0, 12.0, label_visibility="collapsed")
with c3:
    with st.container(border=True):
        st.markdown(f"<div class='header-title'>🔄 Góc quay (°)</div>", unsafe_allow_html=True)
        if 'slew_angle' not in st.session_state: st.session_state.slew_angle = 45
        def update_sl(): st.session_state.slew_angle = st.session_state.s_sl
        def update_nm(): st.session_state.slew_angle = st.session_state.s_nm
        ca, cb = st.columns([1, 2])
        ca.number_input("N", 0, 360, key="s_nm", on_change=update_nm, label_visibility="collapsed")
        cb.slider("S", 0, 360, key="s_sl", on_change=update_sl, label_visibility="collapsed")
        slew_angle = st.session_state.slew_angle

# CALCULATION
specs, _ = get_processed_specs(crane_id, cwt_name, boom_len)
physics_engine = AdvancedCranePhysics(specs)

reach = min(radius - specs['pivot_x'], boom_len * 0.99)
boom_angle = np.degrees(np.arccos(reach/boom_len))

with st.spinner("Đang tính toán..."):
    polar_angles, polar_values = calculate_polar_profile(specs, load_mass, boom_angle, soil_ks, mat_config)

phys_angle_curr = 90 - slew_angle
phys_res_curr = physics_engine.calculate_state(load_mass, boom_angle, phys_angle_curr)

# Mesh & Solver logic
if mat_config['use_left'] or mat_config['use_right']:
    max_L = max(mat_config['L_left'] if mat_config['use_left'] else specs['track_L'],
                mat_config['L_right'] if mat_config['use_right'] else specs['track_L'])
    solve_specs = specs.copy()
    solve_specs['track_L'] = max_L
    solve_specs['track_W'] = max(mat_config['W_left'] if mat_config['use_left'] else specs['track_W'],
                                 mat_config['W_right'] if mat_config['use_right'] else specs['track_W'])
    mesh_gen = AdvancedMeshGenerator(mesh_size=0.05)
    mesh_gen.create_rectangular_mesh(max_L*1.5, specs['track_gauge']*2, default_Ks=soil_ks)
else:
    solve_specs = specs
    mesh_gen = AdvancedMeshGenerator(mesh_size=0.05)
    mesh_gen.create_rectangular_mesh(specs['track_L']*2, specs['track_gauge']*2, default_Ks=soil_ks)

solver = SoilStructureSolver(mesh_gen)
sol_res, err = solver.solve_equilibrium(solve_specs, phys_res_curr, chassis_angle=0)
if err: st.error(err); st.stop()
sol_res['pressure_map'] /= G_CONST
sol_res['pressure_max'] /= G_CONST

# KPI ROW
k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Tổng Tải Trọng</div><div class='kpi-value'>{phys_res_curr['V_total_ton']:.1f} T</div></div>", unsafe_allow_html=True)
with k2:
    col_p = COLOR_LIMIT if sol_res['pressure_max'] > limit_pressure else COLOR_DATA_LINE
    st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Áp Lực Max</div><div class='kpi-value' style='color: {col_p}'>{sol_res['pressure_max']:.2f} t/m²</div></div>", unsafe_allow_html=True)
with k3:
    util = min((sol_res['pressure_max'] / limit_pressure) * 100, 100)
    st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Sử Dụng Tải</div><div class='kpi-value'>{util:.0f}%</div></div>", unsafe_allow_html=True)
with k4:
    safe = sol_res['pressure_max'] <= limit_pressure
    st_cls = "status-safe" if safe else "status-danger"
    st_msg = "AN TOÀN" if safe else "NGUY HIỂM"
    st.markdown(f"<div class='kpi-box'><div class='kpi-label'>Trạng Thái</div><div style='margin-top:5px'><span class='status-badge {st_cls}'>{st_msg}</span></div></div>", unsafe_allow_html=True)

st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

# CHARTS ROW
col_main, col_side = st.columns([1.5, 1])
with col_main:
    with st.container(border=True):
        st.markdown(f"<div class='header-title'>🗺️ Phân bố áp lực chi tiết</div>", unsafe_allow_html=True)
        fig_map, RL, RR, cL, cR = draw_ground_pressure_map_pro(specs, phys_res_curr, sol_res, mesh_gen, slew_angle, mat_config)
        st.pyplot(fig_map)
with col_side:
    with st.container(border=True):
        st.markdown(f"<div class='header-title'>🧭 Ổn định 360° (Polar)</div>", unsafe_allow_html=True)
        fig_polar = draw_polar_chart_pro(polar_angles, polar_values, slew_angle, limit_pressure)
        st.pyplot(fig_polar)

# REPORT TAB
tab_rep, = st.tabs(["🖨️ Báo cáo"])
with tab_rep:
    st.info("Nhấn Ctrl+P để in báo cáo.")
    mat_s = "Không dùng"
    if mat_config['use_left'] or mat_config['use_right']:
        mat_s = f"L:{mat_config['L_left']}x{mat_config['W_left']} | R:{mat_config['L_right']}x{mat_config['W_right']}"
    
    boom_cg = specs.get('boom_cg_radius', 0.0)
    cg_pct = (boom_cg / boom_len * 100) if boom_len > 0 else 0
    
    st.markdown(f"""
    <table class="report-table">
        <tr><td>Model Cẩu</td><td>{crane_id}</td></tr>
        <tr><td>Cấu hình Cần</td><td>{boom_len}m (CG thực tế: {boom_cg:.1f}m ~ {cg_pct:.0f}%)</td></tr>
        <tr><td>Đối trọng</td><td>{cwt_name} ({specs['cwt_mass']}T @ {specs['cwt_radius']}m)</td></tr>
        <tr><td>Tấm lót (Mats)</td><td>{mat_s}</td></tr>
        <tr><td>Tải trọng Hàng</td><td>{load_mass} T</td></tr>
        <tr><td>Bán kính làm việc</td><td>{radius} m</td></tr>
        <tr><td>Tổng trọng lượng vận hành</td><td>{phys_res_curr['V_total_ton']:.1f} T</td></tr>
        <tr><td>Áp lực đất tối đa</td><td>{sol_res['pressure_max']:.2f} t/m²</td></tr>
        <tr><td>Giới hạn cho phép</td><td>{limit_pressure} t/m²</td></tr>
    </table>
    """, unsafe_allow_html=True)