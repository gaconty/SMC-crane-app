import streamlit as st
import numpy as np
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.path import Path
from crane_physics import AdvancedCranePhysics
from solver_engine import SoilStructureSolver
from mesh_engine import AdvancedMeshGenerator
from analysis_engine import calculate_polar_profile
import ai_agent
from config import *
import base64

# [NEW] Set Page Config to Wide Mode
st.set_page_config(
    page_title="SMC Ground Pressure Analysis",
    page_icon="cropped-LOGO-SMC-nho-02-2048x821.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

try:
    logo_b64 = get_base64_image("cropped-LOGO-SMC-nho-02-2048x821.ico")
    logo_html = f'<img src="data:image/x-icon;base64,{logo_b64}" style="height: 50px; vertical-align: middle; margin-right: 15px;">'
    
    # Watermark Image
    watermark_b64 = get_base64_image("cropped-LOGO-SMC-nho-02-2048x821.png")
except:
    logo_html = ""
    watermark_b64 = ""

# --- CSS ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap');
    .stApp {{ 
        background-color: #f8fafc; 
        font-family: 'Roboto', sans-serif; 
        color: {COLOR_TEXT_MAIN}; 
    }}
    
    /* Watermark */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-image: url("data:image/png;base64,{watermark_b64}");
        background-repeat: no-repeat;
        background-position: 60% 50%;
        background-size: 50%;
        opacity: 0.08;
        pointer-events: none;
        z-index: 0;
    }}
    
    /* Ensure content is above watermark */
    .block-container {{
        position: relative;
        z-index: 1;
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
    
    .corner-grid {{
        display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 15px;
    }}
    .corner-box {{
        background: #f8fafc; padding: 8px; border-radius: 6px; text-align: center; border: 1px solid #e2e8f0;
    }}
    .corner-name {{ font-size: 0.7rem; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
    .corner-val {{ font-size: 1.1rem; color: #0f172a; font-weight: 700; }}
    
    .badge-mat {{
        background: #fef3c7; color: #b45309; padding: 2px 6px; border-radius: 4px;
        font-size: 0.7rem; font-weight: 700; border: 1px solid #fcd34d;
    }}
    
    .slew-container {{
        display: flex; align-items: center; justify-content: space-between;
        background: white; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;
    }}
    /* Reduce top whitespace */
    .block-container {{
        padding-top: 3rem !important;
        padding-bottom: 1rem !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown(f"""
    <div style="text-align: center; padding: 10px 0 20px 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 20px;">
        <div style="display: inline-flex; align-items: center; justify-content: center;">
            {logo_html}
            <h1 style="color: #0f172a; font-weight: 800; margin: 0; font-size: 2.2rem;">SMC GROUND PRESSURE</h1>
        </div>
        <p style="color: #64748b; margin-top: 5px; font-size: 0.9rem;">Advanced Crane Ground Bearing Pressure Analysis</p>
    </div>
""", unsafe_allow_html=True)


# --- DATA & CONFIG ---
# --- DATA & CONFIG ---
from backend.crane_manager import CraneManager
from backend.crane_models import CraneData, BaseStructure, CrawlerSystem, CounterweightConfig, BoomSystem, BoomSection, BoomInsert

@st.cache_resource
def get_manager():
    return CraneManager()

manager = get_manager()

def get_crane_options():
    """Trả về danh sách cẩu và đối trọng khả dụng từ Database."""
    cranes = manager.get_all_cranes()
    if not cranes:
        return {}, "Chưa có dữ liệu cẩu. Vui lòng thêm mới trong tab Quản lý."
    
    options = {}
    for c in cranes:
        cwt_names = [cwt.name for cwt in c.counterweight_configs]
        options[c.id] = cwt_names
    return options, None

from backend.boom_logic import generate_boom_configs

@st.cache_data
def get_cached_boom_configs(crane_id):
    """Cache boom configs to avoid re-calculating on every rerun."""
    crane = manager.get_crane(crane_id)
    if not crane: return {}
    return generate_boom_configs(crane)

def get_valid_boom_lengths(crane_id):
    """Trả về danh sách chiều dài cần khả dụng từ cấu hình thực tế."""
    configs = get_cached_boom_configs(crane_id)
    if not configs: return []
    return sorted(list(configs.keys()))

def get_processed_specs(crane_id, cwt_name, boom_len):
    """
    Trả về thông số kỹ thuật chi tiết từ Object CraneData và Boom Config đã tính toán.
    """
    crane = manager.get_crane(crane_id)
    if not crane: return {}, "Không tìm thấy dữ liệu cẩu"

    # Tìm cấu hình đối trọng
    cwt_config = next((c for c in crane.counterweight_configs if c.name == cwt_name), None)
    if not cwt_config: return {}, "Không tìm thấy cấu hình đối trọng"

    # Lấy thông số Boom từ Logic
    configs = get_cached_boom_configs(crane_id)
    # Tìm length gần nhất (do float rounding)
    closest_len = min(configs.keys(), key=lambda x: abs(x - boom_len)) if configs else boom_len
    
    # Nếu sai số quá lớn (>0.1m) thì fallback (không nên xảy ra nếu UI dùng đúng list)
    if abs(closest_len - boom_len) > 0.1:
        # Fallback logic cũ nếu không khớp
        boom_mass = boom_len * 0.2
        boom_cg = boom_len * 0.45
    else:
        cfg = configs[closest_len]
        boom_mass = cfg.total_mass
        boom_cg = cfg.cg_radius

    specs = {
        'boom_len': boom_len,
        'boom_cg_radius': boom_cg,
        'pivot_x': crane.boom_system.pivot_offset_x_m,
        'pivot_z': crane.boom_system.pivot_offset_z_m,
        'carbody_mass': crane.base_structure.carbody_mass_ton,
        'carbody_cwt_mass': cwt_config.carbody_cwt_ton,
        'upper_mass': crane.base_structure.upper_mass_ton,
        'cwt_mass': cwt_config.total_mass_ton,
        'boom_mass': boom_mass,
        'cwt_radius': cwt_config.radius_m,
        'carbody_cg_z': crane.base_structure.carbody_cg_z_m,
        'upper_cg_z': crane.base_structure.upper_cg_z_m,
        'cwt_z': cwt_config.cwt_z_m,
        'track_L': crane.crawler_system.contact_length_m,
        'track_W': crane.crawler_system.shoe_width_m,
        'track_gauge': crane.crawler_system.track_gauge_m
    }
    return specs, None

# --- QUẢN LÝ CẨU UI (IMPROVED) ---
def render_crane_management():
    st.markdown("### 🛠️ QUẢN LÝ THƯ VIỆN CẨU")
    
    # Initialize Session State
    if 'edit_crane_id' not in st.session_state:
        st.session_state.edit_crane_id = None
    if 'duplicate_crane_id' not in st.session_state:
        st.session_state.duplicate_crane_id = None

    tab_list, tab_add = st.tabs(["📂 Danh sách & Tìm kiếm", "✏️ Thêm Mới / Chỉnh Sửa"])
    
    # --- TAB 1: LIST & SEARCH ---
    with tab_list:
        c_search, c_sort = st.columns([3, 1])
        search_term = c_search.text_input("🔍 Tìm kiếm Model", placeholder="Nhập tên hoặc ID cẩu...")
        
        cranes = manager.get_all_cranes()
        if search_term:
            cranes = [c for c in cranes if search_term.lower() in c.model_name.lower() or search_term.lower() in c.id.lower()]
            
        if not cranes:
            st.info("Không tìm thấy dữ liệu cẩu phù hợp.")
        else:
            st.success(f"Tìm thấy {len(cranes)} model.")
            
            # Grid Layout
            cols = st.columns(3)
            for i, c in enumerate(cranes):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"#### 🏗️ {c.model_name}")
                        st.caption(f"ID: `{c.id}`")
                        st.markdown(f"**Max Cap:** `{c.max_capacity_ton} T`")
                        
                        # Mini Stats
                        ms1, ms2 = st.columns(2)
                        ms1.metric("Upper", f"{c.base_structure.upper_mass_ton}t")
                        ms2.metric("Track", f"{c.crawler_system.contact_length_m}m")
                        
                        # Actions
                        b1, b2, b3 = st.columns([1, 1, 1])
                        if b1.button("✏️", key=f"edit_{c.id}", help="Chỉnh sửa"):
                            st.session_state.edit_crane_id = c.id
                            st.session_state.duplicate_crane_id = None
                            st.rerun()
                        
                        if b2.button("📋", key=f"dup_{c.id}", help="Nhân bản"):
                            st.session_state.duplicate_crane_id = c.id
                            st.session_state.edit_crane_id = None # Switch to add mode with pre-fill
                            st.rerun()
                            
                        if b3.button("🗑️", key=f"del_{c.id}", help="Xóa"):
                            if manager.delete_crane(c.id):
                                st.success("Đã xóa!")
                                if st.session_state.edit_crane_id == c.id:
                                    st.session_state.edit_crane_id = None
                                st.rerun()

    # --- TAB 2: ADD / EDIT ---
    with tab_add:
        # Determine Mode
        edit_id = st.session_state.edit_crane_id
        dup_id = st.session_state.duplicate_crane_id
        
        edit_obj = None
        if edit_id:
            edit_obj = manager.get_crane(edit_id)
            st.subheader(f"✏️ Đang chỉnh sửa: {edit_obj.model_name}")
            if st.button("❌ Hủy Chỉnh Sửa"):
                st.session_state.edit_crane_id = None
                st.rerun()
        elif dup_id:
            dup_obj = manager.get_crane(dup_id)
            if dup_obj:
                st.subheader(f"📋 Đang nhân bản từ: {dup_obj.model_name}")
                # Create a copy for pre-filling, but treat as new (no ID lock)
                edit_obj = dup_obj
                # Reset ID for new entry
                # We don't change edit_obj.id here to avoid messing up reference, 
                # but we will handle it in default values.
            if st.button("❌ Hủy Nhân Bản"):
                st.session_state.duplicate_crane_id = None
                st.rerun()
        else:
            st.subheader("🆕 Thêm Model Cẩu Mới")

        # Prepare Default Values
        # If duplicating, we clear ID but keep others. If editing, we keep all.
        d_id = edit_obj.id if (edit_obj and not dup_id) else ("" if not dup_id else f"{edit_obj.id}_COPY")
        d_name = edit_obj.model_name if edit_obj else ""
        d_cap = edit_obj.max_capacity_ton if edit_obj else 80.0
        
        d_upper = edit_obj.base_structure.upper_mass_ton if edit_obj else 30.0
        d_carbody = edit_obj.base_structure.carbody_mass_ton if edit_obj else 10.0
        
        d_gauge = edit_obj.crawler_system.track_gauge_m if edit_obj else 5.0
        d_trk_len = edit_obj.crawler_system.contact_length_m if edit_obj else 6.0
        d_shoe = edit_obj.crawler_system.shoe_width_m if edit_obj else 0.8
        d_trk_mass = edit_obj.crawler_system.track_mass_per_side_ton if edit_obj else 10.0
        
        # Counterweights
        if edit_obj and edit_obj.counterweight_configs:
            default_cwts = [
                {
                    "Name": c.name,
                    "Mass (ton)": c.total_mass_ton,
                    "Radius (m)": c.radius_m,
                    "Carbody Cwt (ton)": c.carbody_cwt_ton
                }
                for c in edit_obj.counterweight_configs
            ]
        else:
            default_cwts = [
                {"Name": "Standard", "Mass (ton)": 30.0, "Radius (m)": 4.5, "Carbody Cwt (ton)": 0.0}
            ]
        
        d_piv_x = edit_obj.boom_system.pivot_offset_x_m if edit_obj else 0.0
        d_piv_z = edit_obj.boom_system.pivot_offset_z_m if edit_obj else 1.8
        
        d_base_len = edit_obj.boom_system.base_section.length_m if edit_obj else 6.0
        d_base_mass = edit_obj.boom_system.base_section.mass_ton if edit_obj else 2.0
        d_base_cg = edit_obj.boom_system.base_section.cg_percent if edit_obj else 0.5
        
        d_tip_len = edit_obj.boom_system.tip_section.length_m if edit_obj else 6.0
        d_tip_mass = edit_obj.boom_system.tip_section.mass_ton if edit_obj else 1.5
        d_tip_cg = edit_obj.boom_system.tip_section.cg_percent if edit_obj else 0.5
        
        # Inserts
        if edit_obj:
            default_inserts = [
                {"ID": i.id, "Length (m)": i.length_m, "Mass (ton)": i.mass_ton, "Quantity": getattr(i, 'quantity', 1)}
                for i in edit_obj.boom_system.inserts
            ]
        else:
            default_inserts = [
                {"ID": "3m", "Length (m)": 3.0, "Mass (ton)": 0.5, "Quantity": 2},
                {"ID": "6m", "Length (m)": 6.0, "Mass (ton)": 0.9, "Quantity": 2},
                {"ID": "12m", "Length (m)": 12.0, "Mass (ton)": 1.6, "Quantity": 1},
            ]

        with st.form("crane_form"):
            # Use Tabs for cleaner UI
            t_gen, t_crawl, t_boom, t_cwt, t_jib = st.tabs(["ℹ️ Thông tin chung", "🚜 Cấu trúc & Di chuyển", "🏗️ Boom System", "⚖️ Đối trọng", "📐 Fixed Jib"])
            
            with t_gen:
                c1, c2 = st.columns(2)
                c_id = c1.text_input("Mã Cẩu (ID)", value=d_id, disabled=bool(edit_id), help="ID là duy nhất")
                c_name = c2.text_input("Tên Model", value=d_name)
                c_cap = st.number_input("Sức nâng Max (Tấn)", value=d_cap)
            
            with t_crawl:
                st.markdown("**Cấu trúc cơ sở**")
                c1, c2 = st.columns(2)
                upper_mass = c1.number_input("Khối lượng quay (Upper Mass)", value=d_upper)
                carbody_mass = c2.number_input("Khối lượng Carbody", value=d_carbody)
                
                st.markdown("**Hệ thống di chuyển (Crawler)**")
                c3, c4 = st.columns(2)
                track_gauge = c3.number_input("Khoảng cách tâm xích (Gauge)", value=d_gauge)
                track_len = c4.number_input("Chiều dài tiếp đất (Contact Length)", value=d_trk_len)
                shoe_width = c3.number_input("Bề rộng bản xích (Shoe Width)", value=d_shoe)
                track_mass = c4.number_input("Khối lượng 1 bên xích", value=d_trk_mass)

            with t_boom:
                st.markdown("**Pivot Point**")
                c1, c2 = st.columns(2)
                pivot_x = c1.number_input("Pivot Offset X", value=d_piv_x)
                pivot_z = c2.number_input("Pivot Offset Z", value=d_piv_z)
                
                st.markdown("**Base & Tip**")
                c_base, c_tip = st.columns(2)
                with c_base:
                    st.caption("Đốt Gốc (Base)")
                    base_len = st.number_input("L Gốc (m)", value=d_base_len)
                    base_mass = st.number_input("M Gốc (Tấn)", value=d_base_mass)
                    base_cg = st.number_input("COG Gốc (%)", value=d_base_cg, min_value=0.0, max_value=1.0)
                with c_tip:
                    st.caption("Đốt Ngọn (Tip)")
                    tip_len = st.number_input("L Ngọn (m)", value=d_tip_len)
                    tip_mass = st.number_input("M Ngọn (Tấn)", value=d_tip_mass)
                    tip_cg = st.number_input("COG Ngọn (%)", value=d_tip_cg, min_value=0.0, max_value=1.0)

                st.markdown("**Danh sách Insert (Đốt nối)**")
                edited_inserts = st.data_editor(
                    default_inserts,
                    num_rows="dynamic",
                    column_config={
                        "ID": st.column_config.TextColumn("Mã", required=True),
                        "Length (m)": st.column_config.NumberColumn("Dài (m)", format="%.1f"),
                        "Mass (ton)": st.column_config.NumberColumn("Nặng (T)", format="%.2f"),
                        "Quantity": st.column_config.NumberColumn("SL", step=1),
                    },
                    width="stretch",
                    key="inserts_editor"
                )

            with t_cwt:
                st.info("Quản lý các cấu hình đối trọng (Ví dụ: Standard, Superlift, Tray...)")
                edited_cwts = st.data_editor(
                    default_cwts,
                    num_rows="dynamic",
                    column_config={
                        "Name": st.column_config.TextColumn("Tên Cấu hình", required=True),
                        "Mass (ton)": st.column_config.NumberColumn("Khối lượng (T)", format="%.1f"),
                        "Radius (m)": st.column_config.NumberColumn("Bán kính (m)", format="%.1f"),
                        "Carbody Cwt (ton)": st.column_config.NumberColumn("Carbody Cwt (T)", format="%.1f"),
                    },
                    width="stretch",
                    key="cwt_editor"
                )
            
            with t_jib:
                st.info("Cấu hình Cần phụ (Fixed Jib)")
                # Prepare default jibs
                if edit_obj and hasattr(edit_obj, 'jib_configs'):
                    default_jibs = [
                        {
                            "Length (m)": j.length_m,
                            "Mass (ton)": j.mass_ton,
                            "Offsets (deg)": ", ".join(map(str, j.offset_angles))
                        }
                        for j in edit_obj.jib_configs
                    ]
                else:
                    default_jibs = []

                edited_jibs = st.data_editor(
                    default_jibs,
                    num_rows="dynamic",
                    column_config={
                        "Length (m)": st.column_config.NumberColumn("Dài (m)", format="%.1f", required=True),
                        "Mass (ton)": st.column_config.NumberColumn("Nặng (T)", format="%.2f", required=True),
                        "Offsets (deg)": st.column_config.TextColumn("Góc nghiêng (cách nhau bởi phẩy)", help="Ví dụ: 10, 30", required=True),
                    },
                    width="stretch",
                    key="jib_editor"
                )

            st.markdown("---")
            btn_text = "💾 Cập nhật Model" if edit_id else "💾 Lưu Cẩu Mới"
            submitted = st.form_submit_button(btn_text, use_container_width=True)
            
            if submitted:
                if not c_id or not c_name:
                    st.error("Vui lòng nhập ID và Tên Model")
                else:
                    # Process Inserts
                    processed_inserts = []
                    for row in edited_inserts:
                        if row["ID"]: 
                            processed_inserts.append(
                                BoomInsert(
                                    id=str(row["ID"]),
                                    length_m=float(row["Length (m)"]),
                                    mass_ton=float(row["Mass (ton)"]),
                                    quantity=int(row["Quantity"])
                                )
                            )
                    
                    # Process Jibs
                    processed_jibs = []
                    for row in edited_jibs:
                        try:
                            offsets = [float(x.strip()) for x in row["Offsets (deg)"].split(",") if x.strip()]
                            processed_jibs.append(
                                JibConfig(
                                    length_m=float(row["Length (m)"]),
                                    mass_ton=float(row["Mass (ton)"]),
                                    offset_angles=offsets
                                )
                            )
                        except ValueError:
                            st.warning(f"Lỗi định dạng góc nghiêng cho Jib dài {row['Length (m)']}m. Bỏ qua.")

                    new_crane = CraneData(
                        id=c_id,
                        model_name=c_name,
                        max_capacity_ton=c_cap,
                        base_structure=BaseStructure(
                            upper_mass_ton=upper_mass,
                            carbody_mass_ton=carbody_mass
                        ),
                        crawler_system=CrawlerSystem(
                            track_mass_per_side_ton=track_mass,
                            contact_length_m=track_len,
                            shoe_width_m=shoe_width,
                            track_gauge_m=track_gauge
                        ),
                        counterweight_configs=[
                            CounterweightConfig(
                                name=str(row["Name"]),
                                total_mass_ton=float(row["Mass (ton)"]),
                                radius_m=float(row["Radius (m)"]),
                                carbody_cwt_ton=float(row["Carbody Cwt (ton)"])
                            )
                            for row in edited_cwts if row["Name"]
                        ],
                        boom_system=BoomSystem(
                            pivot_offset_x_m=pivot_x,
                            pivot_offset_z_m=pivot_z,
                            base_section=BoomSection(length_m=base_len, mass_ton=base_mass, cg_percent=base_cg),
                            tip_section=BoomSection(length_m=tip_len, mass_ton=tip_mass, cg_percent=tip_cg),
                            inserts=processed_inserts
                        ),
                        jib_configs=processed_jibs
                    )
                    
                    if edit_id:
                        # Update Mode
                        if manager.update_crane(c_id, new_crane):
                            st.success(f"Đã cập nhật {c_name}!")
                            st.session_state.edit_crane_id = None
                            st.rerun()
                        else:
                            st.error("Cập nhật thất bại!")
                    else:
                        # Add Mode
                        if manager.add_crane(new_crane):
                            st.success(f"Đã thêm {c_name} thành công!")
                            st.session_state.duplicate_crane_id = None # Clear dup state
                            st.rerun()
                        else:
                            st.error("ID đã tồn tại!")

# --- HELPER: ROBUST PEAK FINDER ---
def get_peak_pressure_in_region(x_center, y_center, width, length, mesh_obj, pressure_map):
    """
    Tìm giá trị áp lực lớn nhất trong vùng lân cận (Robust Region Scan).
    Khắc phục lỗi lấy đúng điểm mép = 0.
    """
    if mesh_obj is None or pressure_map is None: return 0.0
    
    # Xác định vùng quét (Scan Box): +/- 0.5m quanh tâm điểm dò
    # Hoặc quét toàn bộ bề rộng track tại vị trí đầu/cuối
    scan_margin_x = width / 2 + 0.2
    scan_margin_y = 1.0 # Quét 1 mét dọc theo chiều dài
    
    # Tạo mask cho vùng
    mask_region = (mesh_obj.nodes_X >= x_center - scan_margin_x) & \
                  (mesh_obj.nodes_X <= x_center + scan_margin_x) & \
                  (mesh_obj.nodes_Y >= y_center - scan_margin_y) & \
                  (mesh_obj.nodes_Y <= y_center + scan_margin_y)
    
    # Kết hợp với active mask
    final_mask = mask_region & mesh_obj.active_mask
    
    if np.sum(final_mask) == 0: return 0.0
    
    # Lấy max trong vùng
    vals = pressure_map[final_mask] / G_CONST
    return np.max(vals) if len(vals) > 0 else 0.0

# --- HÀM VẼ PRO (CAD STYLE + CLIPPING MASK FIX) ---

def draw_pressure_profile_visual(specs, sol_res, mat_config, limit_p, mesh_obj=None, slew_angle=0):
    """
    Vẽ bản đồ áp lực và hiển thị 4 góc.
    """
    # [FIX] Dynamic Color Scale
    p_max_actual = sol_res['pressure_max'] / G_CONST if sol_res else 0
    vmax_val = max(limit_p * 1.1, p_max_actual)
    
    cmap = LinearSegmentedColormap.from_list("eng_grad", ["#ffffff", "#60a5fa", "#facc15", "#ef4444"])
    norm = Normalize(vmin=0, vmax=vmax_val)

    # Lấy thông số
    gauge = specs['track_gauge']
    trk_W = specs['track_W']
    trk_L = specs['track_L']
    
    if mat_config['use_left']: L_L, W_L, is_mat_L = mat_config['L_left'], mat_config['W_left'], True
    else: L_L, W_L, is_mat_L = trk_L, trk_W, False

    if mat_config['use_right']: L_R, W_R, is_mat_R = mat_config['L_right'], mat_config['W_right'], True
    else: L_R, W_R, is_mat_R = trk_L, trk_W, False

    # --- TÍNH TOÁN 4 GÓC (Robust Scan) ---
    corners = {'FL': 0, 'FR': 0, 'RL': 0, 'RR': 0}
    if mesh_obj and sol_res:
        full_p = sol_res['pressure_map']
        # Front Left (Đầu xích trái): Center X = -gauge/2, Center Y = L_L/2 (approx tip)
        corners['FL'] = get_peak_pressure_in_region(-gauge/2, L_L/2 - 0.5, W_L, 1.0, mesh_obj, full_p)
        # Front Right (Đầu xích phải)
        corners['FR'] = get_peak_pressure_in_region(gauge/2, L_R/2 - 0.5, W_R, 1.0, mesh_obj, full_p)
        # Rear Left (Đuôi xích trái)
        corners['RL'] = get_peak_pressure_in_region(-gauge/2, -L_L/2 + 0.5, W_L, 1.0, mesh_obj, full_p)
        # Rear Right (Đuôi xích phải)
        corners['RR'] = get_peak_pressure_in_region(gauge/2, -L_R/2 + 0.5, W_R, 1.0, mesh_obj, full_p)

        # Tính toán Tải trọng Global (như trước)
        p_map_g = full_p / G_CONST
        mask_L_glob = (mesh_obj.nodes_X < -0.1) & (p_map_g > 0)
        load_real_L = np.sum(p_map_g[mask_L_glob]) * mesh_obj.dA
        mask_R_glob = (mesh_obj.nodes_X > 0.1) & (p_map_g > 0)
        load_real_R = np.sum(p_map_g[mask_R_glob]) * mesh_obj.dA
    else:
        load_real_L = 0; load_real_R = 0

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
    def draw_dim_arrow(p1, p2, text, offset=0, color=COLOR_DIM_LINE):
        x1, y1 = p1; x2, y2 = p2
        is_vert = abs(x1-x2) < 0.1
        
        # Draw Ticks
        ax.plot([x1, x1], [y1, y1+offset], color=color, lw=0.5, alpha=0.5)
        ax.plot([x2, x2], [y2, y2+offset], color=color, lw=0.5, alpha=0.5)
        
        # Draw Arrow
        ax.annotate("", xy=(x1, y1+offset), xytext=(x2, y2+offset),
                    arrowprops=dict(arrowstyle='<->', color=color, lw=1.0, shrinkA=0, shrinkB=0))
        
        # Text Background
        bbox = dict(facecolor='white', edgecolor='none', pad=2, alpha=0.8)
        
        # [FIX] TEXT POSITIONING
        if is_vert:
            # Vertical: Center text between Y1 and Y2
            mid_x = x1
            mid_y = (y1 + y2) / 2 + offset
            ax.text(mid_x, mid_y, text, color=color, fontsize=8, rotation=90, 
                   ha='center', va='center', fontweight='bold', bbox=bbox)
        else:
            # Horizontal: Center text between X1 and X2
            mid_x = (x1 + x2) / 2
            mid_y = y1 + offset
            # Adjust VA based on offset direction
            va = 'bottom' if offset >= 0 else 'top'
            ax.text(mid_x, mid_y, text, color=color, fontsize=8, rotation=0, 
                   ha='center', va=va, fontweight='bold', bbox=bbox)

    # --- 1. VẼ CỤM CHÂN (TRACK + MAT) ---
    def draw_foot(center_x, w_mat, l_mat, has_mat, precalc_load):
        eff_len = 0; eff_pct = 0
        x_min_clip, y_min_clip = center_x - w_mat/2, -l_mat/2
        
        clip_rect = patches.Rectangle((x_min_clip, y_min_clip), w_mat, l_mat, 
                                    transform=ax.transData, fill=False, visible=False)
        ax.add_patch(clip_rect)

        if has_mat:
            rect = patches.Rectangle((x_min_clip, y_min_clip), w_mat, l_mat,
                                   facecolor='#f8fafc', edgecolor='#cbd5e1', lw=1, hatch='///', alpha=0.5, zorder=1)
            ax.add_patch(rect)
            ax.add_patch(patches.Rectangle((x_min_clip, y_min_clip), w_mat, l_mat,
                                          facecolor='none', edgecolor='#94a3b8', lw=1, zorder=1))

        if mesh_obj:
            X_coords = mesh_obj.nodes_X[0, :]
            Y_coords = mesh_obj.nodes_Y[:, 0]
            
            def find_nearest_idx(arr, val): return np.argmin(np.abs(arr - val))

            idx_x_min = find_nearest_idx(X_coords, x_min_clip)
            idx_x_max = find_nearest_idx(X_coords, x_min_clip + w_mat) + 1 
            idx_y_min = find_nearest_idx(Y_coords, y_min_clip)
            idx_y_max = find_nearest_idx(Y_coords, y_min_clip + l_mat) + 1
            
            idx_x_max = min(idx_x_max, len(X_coords))
            idx_y_max = min(idx_y_max, len(Y_coords))

            Z_map = sol_res['pressure_map'][idx_y_min:idx_y_max, idx_x_min:idx_x_max] / G_CONST
            X_plot = X_coords[idx_x_min:idx_x_max]
            Y_plot = Y_coords[idx_y_min:idx_y_max]
            
            if Z_map.shape[0] > 0 and Z_map.shape[1] > 0:
                if X_plot.size == Z_map.shape[1] and Y_plot.size == Z_map.shape[0]:
                     ax.pcolormesh(X_plot, Y_plot, Z_map, cmap=cmap, norm=norm, shading='nearest', zorder=2)
                
                ps_all = sol_res['pressure_map'] / G_CONST
                local_mask = (mesh_obj.nodes_X >= x_min_clip) & (mesh_obj.nodes_X <= x_min_clip + w_mat) & \
                             (mesh_obj.nodes_Y >= y_min_clip) & (mesh_obj.nodes_Y <= y_min_clip + l_mat) & \
                             (mesh_obj.active_mask)
                contact_nodes_mask = local_mask & (ps_all > 0.1)
                total_nodes = np.sum(local_mask)
                contact_area_nodes = np.sum(contact_nodes_mask)
                eff_pct = (contact_area_nodes / total_nodes * 100) if total_nodes > 0 else 0
                eff_len = (contact_area_nodes * mesh_obj.dA) / w_mat if w_mat > 0 else 0

        # C. XÍCH CẨU (Lớp trên cùng)
        ax.add_patch(patches.Rectangle((center_x - trk_W/2, -trk_L/2), trk_W, trk_L,
                                     facecolor='none', edgecolor=COLOR_TRACK_OUTLINE, lw=2, zorder=10))
        n_pads = 12
        pad_step = trk_L / n_pads
        for y in np.arange(-trk_L/2, trk_L/2, pad_step):
            ax.plot([center_x - trk_W/2, center_x + trk_W/2], [y, y], color=COLOR_TRACK_OUTLINE, lw=0.5, alpha=0.6, zorder=10)
        ax.plot(center_x, trk_L/2 + 0.2, '^', color=COLOR_TRACK_OUTLINE, ms=6, zorder=10)
        ax.plot(center_x, -trk_L/2 - 0.2, 'v', color=COLOR_TRACK_OUTLINE, ms=6, zorder=10)

        # D. KÍCH THƯỚC
        side = 1 if center_x > 0 else -1
        draw_dim_arrow((center_x + (w_mat/2 + 0.5)*side, -l_mat/2), 
                       (center_x + (w_mat/2 + 0.5)*side, l_mat/2), 
                       f"{l_mat}m", offset=0.2*side)
        draw_dim_arrow((center_x - w_mat/2, -limit_y + 0.8),
                       (center_x + w_mat/2, -limit_y + 0.8),
                       f"{w_mat}m", offset=-0.2)

        return precalc_load, eff_len, eff_pct

    # Vẽ Trái/Phải
    l_L, e_L, pct_L = draw_foot(-gauge/2, W_L, L_L, is_mat_L, load_real_L)
    l_R, e_R, pct_R = draw_foot(gauge/2, W_R, L_R, is_mat_R, load_real_R)

    # --- VẼ LABEL 4 GÓC TRỰC TIẾP TRÊN BẢN ĐỒ ---
    def draw_corner_label(x, y, val, align_x='center', align_y='bottom'):
        txt_col = COLOR_DANGER if val > limit_p else '#1e293b'
        bg_col = 'white'
        box_props = dict(boxstyle='round,pad=0.2', facecolor=bg_col, edgecolor='#cbd5e1', alpha=0.9)
        ax.text(x, y, f"{val:.1f}", color=txt_col, fontweight='bold', fontsize=9, 
                ha=align_x, va=align_y, bbox=box_props, zorder=20)
    
    # Vẽ 4 góc (Căn chỉnh để không che hình)
    draw_corner_label(-gauge/2, L_L/2 + 0.5, corners['FL'], 'center', 'bottom')
    draw_corner_label(gauge/2, L_R/2 + 0.5, corners['FR'], 'center', 'bottom')
    draw_corner_label(-gauge/2, -L_L/2 - 0.5, corners['RL'], 'center', 'top')
    draw_corner_label(gauge/2, -L_R/2 - 0.5, corners['RR'], 'center', 'top')

    # --- 2. VẼ THÂN MÁY (CARBODY) ---
    draw_dim_arrow((-gauge/2, limit_y - 0.8), (gauge/2, limit_y - 0.8), f"{gauge}m", offset=0.3)

    beam_h = 0.4
    ax.add_patch(patches.Rectangle((-gauge/2, -beam_h/2), gauge, beam_h, facecolor=COLOR_STEEL, edgecolor='none', zorder=5))
    
    cb_w = gauge - trk_W - 1.0; cb_h = cb_w * 0.8 
    if cb_h > trk_L * 0.6: cb_h = trk_L * 0.6
    
    rect_cb = patches.Rectangle((-cb_w/2, -cb_h/2), cb_w, cb_h, facecolor='#f1f5f9', edgecolor=COLOR_STEEL, lw=2, zorder=6)
    ax.add_patch(rect_cb)
    ax.plot([-cb_w/2, cb_w/2], [-cb_h/2, cb_h/2], color=COLOR_STEEL, lw=1, alpha=0.3, zorder=6)
    ax.plot([-cb_w/2, cb_w/2], [cb_h/2, -cb_h/2], color=COLOR_STEEL, lw=1, alpha=0.3, zorder=6)

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

    ax.text(0, -limit_y + 1.5, f"góc quay: {slew_angle}°", ha='center', fontsize=10, fontweight='bold', 
            bbox=dict(facecolor='white', edgecolor='#e2e8f0', boxstyle='round,pad=0.3'))

    # --- 3. LEGEND ---
    cbar_w = gauge * 0.8; cbar_h = 0.3
    cbar_x = -cbar_w/2; cbar_y = limit_y - 2.0
    grad = np.linspace(0, 1, 256); grad = np.vstack((grad, grad))
    ax.imshow(grad, aspect='auto', cmap=cmap, extent=[cbar_x, cbar_x+cbar_w, cbar_y, cbar_y+cbar_h], zorder=10)
    ax.add_patch(patches.Rectangle((cbar_x, cbar_y), cbar_w, cbar_h, fill=False, edgecolor='#94a3b8', lw=0.5, zorder=11))
    
    ax.text(cbar_x, cbar_y+cbar_h+0.15, "0 t/m²", ha='center', fontsize=7, color='#64748b')
    ax.text(cbar_x+cbar_w, cbar_y+cbar_h+0.15, f"{vmax_val:.1f}", ha='center', fontsize=7, color=COLOR_DANGER, fontweight='bold')
    ax.text(0, cbar_y+cbar_h+0.15, "GROUND PRESSURE", ha='center', fontsize=7, fontweight='bold', color='#334155')

    return fig, l_L, l_R, e_L, e_R, pct_L, pct_R, corners

# --- HÀM VẼ POLAR PRO (Chi tiết hơn) ---
def draw_polar_chart_pro(angles, p_values, current_slew, limit_p=30.0):
    theta = np.radians(angles)
    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={'projection': 'polar'}, facecolor='white')
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    
    # Grid đậm và chi tiết hơn
    ax.grid(color="#032349", linestyle='-', linewidth=0.8, alpha=0.6)
    
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

# ==============================================================================
# MAIN UI LAYOUT
# ==============================================================================

# Sidebar Mode Selection
mode = st.sidebar.radio("Chế độ", ["🔥 Tính toán Áp lực", "🛠️ Quản lý Thư viện Cẩu"])

if mode == "🛠️ Quản lý Thư viện Cẩu":
    render_crane_management()
    st.stop() # Stop execution here for management mode

# --- CALCULATOR MODE ---


with st.sidebar:
    st.markdown("### 🏗️ CẤU HÌNH CẨU")
    options, msg = get_crane_options()
    if not options: st.error(msg); st.stop()
    
    with st.expander("1. THIẾT BỊ", expanded=True):
        crane_id = st.selectbox("Model", list(options.keys()))
        cwt_name = st.selectbox("Đối trọng", options[crane_id])
        valid_lens = get_valid_boom_lengths(crane_id)
        boom_len = st.select_slider("Chiều dài Cần (m)", options=valid_lens) if valid_lens else st.number_input("Cần (m)", 60.0)
        
        # Jib Configuration
        # Get current crane object to check for Jibs
        current_crane = manager.get_crane(crane_id)
        has_jibs = current_crane and hasattr(current_crane, 'jib_configs') and len(current_crane.jib_configs) > 0
        
        use_jib = st.checkbox("Sử dụng Cần phụ (Fixed Jib)", value=False, disabled=not has_jibs)
        if not has_jibs and use_jib:
             st.warning("Model cẩu này chưa được cấu hình Jib. Vui lòng vào tab Quản lý để thêm.")
             use_jib = False

        jib_len = 0.0
        jib_offset = 0.0
        jib_mass = 0.0
        
        if use_jib:
            # Get Jib Options from DB
            jib_opts = {j.length_m: j for j in current_crane.jib_configs}
            sorted_lens = sorted(list(jib_opts.keys()))
            
            c_jib1, c_jib2 = st.columns(2)
            jib_len = c_jib1.selectbox("Jib Length (m)", sorted_lens)
            
            # Get offsets for selected length
            selected_jib = jib_opts[jib_len]
            jib_offsets = selected_jib.offset_angles
            jib_offset = c_jib2.selectbox("Jib Offset (deg)", jib_offsets)
            
            jib_mass = selected_jib.mass_ton

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

    with st.expander("3. TẢI TRỌNG & BÁN KÍNH", expanded=True):
        load_mass = st.number_input("Tải trọng (Tấn)", value=50.0, step=1.0)
        radius = st.number_input("Bán kính (m)", value=12.0, step=0.5)
        load_height_z = st.number_input("Chiều cao nâng Z (m)", value=0.0, step=1.0, help="Chiều cao cần đưa hàng lên")
        # Slew Angle with Sync
        if 'slew_angle' not in st.session_state:
            st.session_state.slew_angle = 0

        def update_slew_slider():
            st.session_state.slew_angle = st.session_state.slew_slider_key
        def update_slew_input():
            st.session_state.slew_angle = st.session_state.slew_input_key

        c_slew1, c_slew2 = st.columns([3, 1])
        with c_slew1:
            st.slider("Góc quay (độ)", 0, 360, key="slew_slider_key", value=st.session_state.slew_angle, step=5, on_change=update_slew_slider)
        with c_slew2:
            st.number_input("Nhập góc", 0, 360, key="slew_input_key", value=st.session_state.slew_angle, step=1, on_change=update_slew_input)
        
        slew_angle = st.session_state.slew_angle

    with st.expander("4. THÔNG SỐ ĐẤT", expanded=True):
        soil_ks = st.number_input("Hệ số nền Ks (kN/m3)", value=10000.0, step=1000.0)
        limit_pressure = st.number_input("Giới hạn áp lực (t/m2)", value=20.0, step=1.0)
        
        # --- AI PREDICTION UI ---
        if st.checkbox("🔮 Dự đoán đất (AI)", value=False):
            st.info("Sử dụng AI để gợi ý Ks và P_allow")
            c_soil, c_moist = st.columns(2)
            soil_type = c_soil.selectbox("Loại đất", ["Clay", "Sand", "Silt", "Gravel"])
            moisture = c_moist.selectbox("Độ ẩm", ["Low", "Medium", "High"])
            
            if st.button("Áp dụng gợi ý"):
                pred_ks, pred_p = ai_agent.OfflineAIAgent().predict_soil_params(soil_type, moisture)
                st.success(f"Gợi ý: Ks={pred_ks:.0f}, P_allow={pred_p:.1f}")



# PROCESS DATA
specs, _ = get_processed_specs(crane_id, cwt_name, boom_len)
specs['slope_grade_x_pct'] = slope_x
specs['slope_roll_y_pct'] = slope_y

physics_engine = AdvancedCranePhysics(specs)
reach = min(radius - specs['pivot_x'], boom_len * 0.99)
boom_angle = np.degrees(np.arccos(reach/boom_len))

# [NEW] Check Tip Height (Updated for Jib)
if use_jib:
    # Approx check for Jib
    jib_rad = np.radians(boom_angle - jib_offset)
    tip_height = specs['pivot_z'] + boom_len * np.sin(np.radians(boom_angle)) + jib_len * np.sin(jib_rad)
else:
    tip_height = specs['pivot_z'] + boom_len * np.sin(np.radians(boom_angle))

if tip_height < load_height_z:
    st.warning(f"⚠️ Chiều cao đầu cần ({tip_height:.1f}m) thấp hơn chiều cao nâng yêu cầu ({load_height_z}m)!")

phys_res = physics_engine.calculate_state(
    load_mass, boom_angle, 90 - slew_angle, 
    jib_length=jib_len, jib_offset_deg=jib_offset, jib_mass=jib_mass
)

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

# [FIX] Added Error Handling
try:
    sol_res, err = solver.solve_equilibrium(solve_specs, phys_res)
    if err: 
        st.error(f"Lỗi tính toán: {err}")
        st.stop()
except Exception as e:
    st.error(f"Lỗi nghiêm trọng: {str(e)}")
    st.stop()

# Initialize AI Learning (Moved up)
from backend.ai_learning import CraneAILearning
if 'ai_learner' not in st.session_state:
    st.session_state.ai_learner = CraneAILearning()
learner = st.session_state.ai_learner

# DASHBOARD HEADER (UPDATED PHASE 2)
p_max = sol_res['pressure_max'] / G_CONST
sliding_force = np.sqrt(phys_res['Fx_slide_ton']**2 + phys_res['Fy_slide_ton']**2)
sf_slide = (phys_res['V_total_ton'] * 0.3) / (sliding_force + 1e-3)
sf_bearing = limit_pressure / p_max # Hệ số an toàn chịu tải nền

# Thông số Solver AI
n_iter = sol_res.get('solver_iters', 0)
cost_val = sol_res.get('solver_cost', 0)

k1, k2, k3, k4, k5 = st.columns([1, 1, 1, 1, 1.5])
with k1: 
    st.metric("ÁP LỰC MAX", f"{p_max:.2f} t/m²", 
             delta=f"{limit_pressure-p_max:.1f} dư", 
             delta_color="normal" if p_max < limit_pressure else "inverse")
with k2: 
    st.metric("TỔNG TẢI", f"{phys_res['V_total_ton']:.1f} T")
with k3: 
    st.metric("MÔ-MEN", f"{phys_res['Mz_yaw_Tm']:.1f} Tm")
with k4: 
    st.metric("HS AN TOÀN NỀN", f"{sf_bearing:.2f}", 
             delta="Đủ tải" if sf_bearing>1.0 else "Sụt lún", 
             delta_color="normal" if sf_bearing>1.0 else "inverse")
with k5:
    if st.button("🤖 AUTO AI CALCULATION", help="Chạy mô phỏng chuyên sâu: 360 độ, tải trọng & bán kính ngẫu nhiên"):
        with st.spinner("Đang chạy mô phỏng Deep Learning (0-360°)..."):
            # Get limits
            crane_obj = manager.get_crane(crane_id)
            max_cap = crane_obj.max_capacity_ton if crane_obj else 100.0
            
            sim_angles = range(0, 360, 1) # Step 1 degree
            max_p_sim = 0
            min_sf_sim = 999
            valid_count = 0
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, ang in enumerate(sim_angles):
                # Generate Random Scenario
                # Load: 5% -> 100% Max Cap
                sim_load = random.uniform(max_cap * 0.05, max_cap)
                # Radius: 3m -> 70% Boom Len
                sim_radius = random.uniform(3.0, boom_len * 0.7)
                
                status_text.text(f"Simulating: Angle {ang}°, Load {sim_load:.1f}t, Rad {sim_radius:.1f}m")
                
                # Calculate Physics for this scenario
                # Need to recalc boom angle for new radius
                sim_reach = min(sim_radius - specs['pivot_x'], boom_len * 0.99)
                sim_boom_angle = np.degrees(np.arccos(sim_reach/boom_len))
                
                p_res_sim = physics_engine.calculate_state(sim_load, sim_boom_angle, 90 - ang)
                
                # Sim Solver
                # We use the CURRENT ground specs (soil_ks) for simulation
                s_res_sim, err_sim = solver.solve_equilibrium(solve_specs, p_res_sim)
                
                if not err_sim:
                    p_val = s_res_sim['pressure_max'] / G_CONST
                    sf_val = limit_pressure / p_val if p_val > 0 else 999
                    
                    max_p_sim = max(max_p_sim, p_val)
                    min_sf_sim = min(min_sf_sim, sf_val)
                    valid_count += 1
                    
                    # Log to AI
                    log_inputs = {
                        'load_mass': sim_load, 'radius': sim_radius, 'boom_len': boom_len,
                        'slew_angle': ang, 'soil_ks': soil_ks, 'cwt_mass': specs['cwt_mass'],
                        'mat_L': solve_specs['track_L'], 'mat_W': solve_specs['track_W']
                    }
                    log_outputs = {'p_max': p_val, 'safety_factor': sf_val}
                    learner.log_calculation(log_inputs, log_outputs)
                
                progress_bar.progress((i + 1) / len(sim_angles))
            
            status_text.empty()
            # Train model
            train_msg = learner.train_model()
            st.success(f"✅ Deep Simulation Hoàn tất! {valid_count} kịch bản. Max P: {max_p_sim:.2f}, Min SF: {min_sf_sim:.2f}. {train_msg}")

st.markdown("---")

# DASHBOARD BODY
# DASHBOARD BODY
c_map, c_polar = st.columns([2, 1])

with c_map:
    st.markdown("#### 🗺️ BẢN ĐỒ ÁP LỰC CHI TIẾT")
    # [FIX] Nhận thêm biến corners từ hàm vẽ
    fig_map, lL, lR, eL, eR, pct_L, pct_R, corners = draw_pressure_profile_visual(specs, sol_res, mat_config, limit_pressure, mesh_gen, slew_angle)
    st.pyplot(fig_map, width='stretch')

with c_polar:
    st.markdown("#### 🧭 SƠ ĐỒ ỔN ĐỊNH°")
    angles, vals = calculate_polar_profile(specs, load_mass, boom_angle, soil_ks, mat_config)
    fig_polar = draw_polar_chart_pro(angles, vals, slew_angle, limit_pressure)
    st.pyplot(fig_polar, width='stretch')

st.markdown("---")
st.markdown("#### 📊 THÔNG SỐ CHI TIẾT")

# Calculate Max Pressure Angle from Polar Data
max_p_idx = np.argmax(vals)
max_p_val = vals[max_p_idx]
max_p_angle = angles[max_p_idx]

c_stat1, c_stat2, c_stat3 = st.columns([1.2, 1.2, 1])

with c_stat1:
    # Display 4 Corners (Lấy giá trị từ hàm vẽ để đồng bộ)
    st.markdown("""
    <div class="info-panel">
        <div class="panel-title">GIÁ TRỊ 4 GÓC (t/m²)</div>
        <div class="corner-grid">
            <div class="corner-box">
                <div class="corner-name">TRƯỚC TRÁI</div>
                <div class="corner-val">{:.2f}</div>
            </div>
            <div class="corner-box">
                <div class="corner-name">TRƯỚC PHẢI</div>
                <div class="corner-val">{:.2f}</div>
            </div>
            <div class="corner-box">
                <div class="corner-name">SAU TRÁI</div>
                <div class="corner-val">{:.2f}</div>
            </div>
            <div class="corner-box">
                <div class="corner-name">SAU PHẢI</div>
                <div class="corner-val">{:.2f}</div>
            </div>
        </div>
        <div style="margin-top: 10px; padding-top: 5px; border-top: 1px solid #eee; font-size: 0.9em; color: #d9534f;">
            <strong>⚠️ Góc nguy hiểm nhất:</strong> {}° (P_max = {:.2f} t/m²)
        </div>
    </div>
    """.format(corners['FL'], corners['FR'], corners['RL'], corners['RR'], max_p_angle, max_p_val), unsafe_allow_html=True)

with c_stat2:
    # Card Left
    st.markdown(f"""
    <div class="info-panel">
        <div class="panel-title">TRACK INFO (Xích & Tấm lót) {'<span class="badge-mat">MATS</span>' if mat_config['use_left'] or mat_config['use_right'] else ''}</div>
        <div style="display: flex; justify-content: space-between;">
            <div style="width: 48%;">
                <div class="track-row" style="font-weight:bold; border-bottom:1px solid #eee;">LEFT TRACK</div>
                <div class="track-row"><span class="track-label">Tải trọng:</span> <span class="track-val">{lL:.1f} T</span></div>
                <div class="track-row"><span class="track-label">Hiệu quả:</span> <span class="track-val">{pct_L:.0f}%</span></div>
                <div class="track-row"><span class="track-label">Chiều dài ép:</span> <span class="track-val">{eL:.2f} m</span></div>
            </div>
            <div style="width: 48%;">
                <div class="track-row" style="font-weight:bold; border-bottom:1px solid #eee;">RIGHT TRACK</div>
                <div class="track-row"><span class="track-label">Tải trọng:</span> <span class="track-val">{lR:.1f} T</span></div>
                <div class="track-row"><span class="track-label">Hiệu quả:</span> <span class="track-val">{pct_R:.0f}%</span></div>
                <div class="track-row"><span class="track-label">Chiều dài ép:</span> <span class="track-val">{eR:.2f} m</span></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c_stat3:
    # Load Breakdown
    total_load = phys_res['V_total_ton']
    st.markdown(f"""
    <div class="info-panel">
        <div class="panel-title">CHI TIẾT TẢI TRỌNG (Tấn)</div>
        <div class="track-row"><span class="track-label">Upper Structure:</span> <span class="track-val">{specs['upper_mass']:.1f}</span></div>
        <div class="track-row"><span class="track-label">Carbody + Cwt:</span> <span class="track-val">{specs['carbody_mass'] + specs.get('carbody_cwt_mass', 0):.1f}</span></div>
        <div class="track-row"><span class="track-label">Counterweight:</span> <span class="track-val">{specs['cwt_mass']:.1f}</span></div>
        <div class="track-row"><span class="track-label">Boom System:</span> <span class="track-val">{specs['boom_mass']:.1f}</span></div>
        <div class="track-row"><span class="track-label">Jib:</span> <span class="track-val">{jib_mass:.1f}</span></div>
        <div class="track-row"><span class="track-label">Live Load:</span> <span class="track-val">{load_mass:.1f}</span></div>
        <div class="track-row" style="border-top:2px solid #333; margin-top:5px; padding-top:5px; font-size: 1.1em;">
            <span class="track-label"><strong>TOTAL:</strong></span> <span class="track-val"><strong>{total_load:.1f}</strong></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- AI AGENT SECTION (BELOW DASHBOARD) ---
st.markdown("---")

# Learner already initialized at top

# LOGGING LOGIC (Auto-log if calculation successful)
if 'sol_res' in locals() and sol_res and not err:
    # Prepare data
    log_inputs = {
        'load_mass': load_mass,
        'radius': radius,
        'boom_len': boom_len,
        'slew_angle': slew_angle,
        'soil_ks': soil_ks,
        'cwt_mass': specs['cwt_mass'],
        'mat_L': solve_specs['track_L'],
        'mat_W': solve_specs['track_W']
    }
    log_outputs = {
        'p_max': p_max,
        'safety_factor': sf_bearing
    }
    # Log to CSV
    learner.log_calculation(log_inputs, log_outputs)

# AI PREDICTION (Quick Check)
if learner.is_trained:
    with st.sidebar.expander("🤖 AI Quick Check", expanded=True):
        st.caption("Dự đoán nhanh kết quả:")
        pred_inputs = {
            'load_mass': load_mass,
            'radius': radius,
            'boom_len': boom_len,
            'slew_angle': slew_angle,
            'soil_ks': soil_ks,
            'cwt_mass': specs['cwt_mass'],
            'mat_L': solve_specs['track_L'],
            'mat_W': solve_specs['track_W']
        }
        pred = learner.predict(pred_inputs)
        if pred:
            st.metric("P_max (AI)", f"{pred['p_max']:.2f} t/m²")
            st.metric("Safety Factor (AI)", f"{pred['safety_factor']:.2f}")
        else:
            st.warning("AI chưa sẵn sàng.")

st.header("🤖 AI AGENT (OFFLINE)")

# Instantiate the agent
# Instantiate the agent
agent = ai_agent.OfflineAIAgent()

tab1, tab2, tab3 = st.tabs(["Tối ưu hóa Cấu hình", "Phân tích Rủi ro", "🧠 AI Self-Learning"])

with tab1:
    st.write("Tự động tìm kích thước tấm lót tối ưu để tiết kiệm chi phí.")
    if st.button("🚀 Chạy Tối ưu hóa (Bayesian Opt)"):
        with st.spinner("Đang chạy mô phỏng AI..."):
            # Use full specs from main logic
            opt_res, msg = agent.optimize_configuration(
                specs, load_mass, radius, boom_angle, slew_angle, soil_ks, limit_pressure
            )
        
        if opt_res:
            st.success("Đã tìm thấy cấu hình tối ưu!")
            c1, c2, c3 = st.columns(3)
            c1.metric("L Tấm lót", f"{opt_res['optimal_L']} m")
            c2.metric("W Tấm lót", f"{opt_res['optimal_W']} m")
            c3.metric("Score (Cost)", f"{opt_res['min_cost_score']:.1f}")
        else:
            st.error(msg)

with tab2:
    st.write("Chạy mô phỏng Monte Carlo (100 lần) để đánh giá xác suất sự cố.")
    if st.button("🎲 Chạy Phân tích Rủi ro"):
        with st.spinner("Đang chạy 100 mô phỏng..."):
            # Use full specs
            risk_res = agent.run_risk_analysis(
                specs, load_mass, radius, boom_angle, slew_angle, soil_ks, limit_pressure, n_simulations=100
            )
        
        if risk_res:
            st.write(f"**Xác suất quá tải nền:** {risk_res['failure_prob_pct']:.1f}%")
            st.write(f"**Áp lực Max trung bình:** {risk_res['mean_p_max']:.2f} t/m²")
            st.write(f"**Độ lệch chuẩn:** {risk_res['std_p_max']:.2f}")
            
            if risk_res['failure_prob_pct'] > 5.0:
                st.error("⚠️ Rủi ro cao! Cần xem xét lại cấu hình.")
            else:
                st.success("✅ Rủi ro thấp. An toàn.")

with tab3:
    st.markdown("### 🧠 AI Tự Học (Machine Learning)")
    st.info("Hệ thống tự động ghi lại lịch sử tính toán để 'học' và đưa ra dự đoán nhanh.")
    
    # Show Stats
    history = learner.get_history()
    st.metric("Dữ liệu đã học", f"{len(history)} bản ghi")
    
    if not history.empty:
        with st.expander("Xem lịch sử tính toán"):
            st.dataframe(history.tail(10))
            
    if st.button("🎓 Huấn luyện lại Mô hình AI"):
        with st.spinner("Đang training..."):
            res = learner.train_model()
        if "Success" in res:
            st.success(res)
        else:
            st.error(res)
            st.error(res)

# --- FOOTER ---
st.markdown("""
    <div style="text-align: center; padding: 20px; margin-top: 50px; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 0.8rem;">
        develop by <b>SMC Services and Engineering</b>
    </div>
""", unsafe_allow_html=True)


