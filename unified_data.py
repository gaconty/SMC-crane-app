import json
import os

CRANE_DATA_FILE = 'crane_data_library.json'

# ==============================================================================
# 1. DATABASE ACCESS
# ==============================================================================

def load_full_database(file_path=CRANE_DATA_FILE):
    """Tải toàn bộ file JSON."""
    if not os.path.exists(file_path):
        return None, f"Không tìm thấy file: {file_path}"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Chuyển list thành dict với key là id để truy xuất nhanh
        return {c['id']: c for c in data.get('cranes', [])}, None
    except Exception as e:
        return None, str(e)

def get_crane_options():
    """Lấy danh sách ID và cấu hình đối trọng để hiển thị UI."""
    db, msg = load_full_database()
    if not db: return None, msg
    
    options = {}
    for cid, data in db.items():
        configs = [cfg['name'] for cfg in data.get('counterweight_configs', [])]
        options[cid] = configs
    
    return options, None

def get_valid_boom_lengths(crane_id):
    """
    Trả về danh sách các chiều dài cần hợp lệ (Valid Configurations).
    Logic: Base + Tip + tổ hợp các Inserts.
    Để đơn giản hóa cho UI: Tạo bước nhảy dựa trên đốt insert nhỏ nhất.
    """
    db, _ = load_full_database()
    if not db or crane_id not in db: return []
    
    boom_sys = db[crane_id]['boom_system']
    
    # Chiều dài tối thiểu = Gốc + Ngọn
    min_len = boom_sys['base_section']['length_m'] + boom_sys['tip_section']['length_m']
    
    # Tìm bước nhảy nhỏ nhất (thường là 3m)
    inserts = boom_sys.get('inserts', [])
    if not inserts:
        return [min_len]
    
    step = min(ins['length_m'] for ins in inserts)
    
    # Giả lập các chiều dài (Max khoảng 100m - 150m tùy loại)
    # Trong thực tế phần mềm PRO sẽ dùng đệ quy để tìm tất cả tổ hợp
    # Ở đây ta dùng cấp số cộng để tạo List cho Slider
    valid_lengths = []
    current = min_len
    while current <= 150.0: # Giới hạn cứng tạm thời
        valid_lengths.append(current)
        current += step
        
    return valid_lengths

# ==============================================================================
# 2. BOOM ASSEMBLY LOGIC (CORE ALGORITHM)
# ==============================================================================

def assemble_boom(boom_sys, target_len):
    """
    Thuật toán 'Greedy': Lắp ghép các đốt để đạt chiều dài mong muốn.
    Ưu tiên dùng đốt dài trước để giảm số lượng mối nối.
    """
    base = boom_sys['base_section']
    tip = boom_sys['tip_section']
    
    # Chiều dài cố định
    fixed_len = base['length_m'] + tip['length_m']
    needed_len = target_len - fixed_len
    
    # Lấy danh sách inserts và sắp xếp giảm dần theo chiều dài
    available_inserts = sorted(boom_sys.get('inserts', []), key=lambda x: x['length_m'], reverse=True)
    
    chosen_inserts = []
    
    # Logic lắp ghép (đơn giản hóa: cho phép lặp lại đốt vô hạn)
    remaining = needed_len
    
    # Sai số cho phép (do sai số làm tròn float)
    epsilon = 0.05 
    
    for ins in available_inserts:
        while remaining >= ins['length_m'] - epsilon:
            chosen_inserts.append(ins)
            remaining -= ins['length_m']
            
    # Tính lại chiều dài thực tế cuối cùng
    final_len = fixed_len + sum(i['length_m'] for i in chosen_inserts)
    
    return {
        "base": base,
        "tip": tip,
        "inserts": chosen_inserts,
        "total_len": final_len
    }

def calculate_boom_physics(assembly_config):
    """
    Tính Toán Cơ Học Cần:
    1. Tổng khối lượng (Total Mass)
    2. Vị trí trọng tâm tổng hợp (Composite CG) tính từ chốt chân cần (Pivot).
    Sử dụng nguyên lý Momen tĩnh (Moment of Moments).
    """
    base = assembly_config['base']
    tip = assembly_config['tip']
    inserts = assembly_config['inserts']
    
    total_mass = 0.0
    total_moment = 0.0
    
    current_x = 0.0 # Vị trí bắt đầu của đốt hiện tại (tính từ chốt)
    
    # 1. Xử lý Đốt Gốc (Base)
    m_base = base['mass_ton']
    # CG local của Base tính từ đầu chốt
    cg_local = base['length_m'] * base.get('cg_percent', 0.5) 
    cg_global = current_x + cg_local
    
    total_mass += m_base
    total_moment += m_base * cg_global
    
    current_x += base['length_m']
    
    # 2. Xử lý Các Đốt Giữa (Inserts)
    for ins in inserts:
        m_ins = ins['mass_ton']
        # Inserts thường đối xứng, CG nằm giữa
        cg_global = current_x + (ins['length_m'] * 0.5)
        
        total_mass += m_ins
        total_moment += m_ins * cg_global
        
        current_x += ins['length_m']
        
    # 3. Xử lý Đốt Ngọn (Tip)
    m_tip = tip['mass_ton']
    # CG local của Tip tính từ điểm nối với đốt trước
    cg_local = tip['length_m'] * tip.get('cg_percent', 0.5)
    cg_global = current_x + cg_local
    
    total_mass += m_tip
    total_moment += m_tip * cg_global
    
    # Tính CG tổng hợp (Khoảng cách từ chốt chân cần)
    cg_radius = total_moment / total_mass if total_mass > 0 else 0
    
    return total_mass, cg_radius

# ==============================================================================
# 3. MAIN DATA PROCESSOR
# ==============================================================================

def get_processed_specs(crane_id, cwt_name, target_boom_len):
    """
    Hàm chính được UI và Solver gọi.
    Trả về specs đầy đủ đã tính toán vật lý chính xác.
    """
    db, msg = load_full_database()
    if not db or crane_id not in db:
        return None, "Không tìm thấy dữ liệu cẩu."
    
    crane = db[crane_id]
    
    # --- A. CẤU HÌNH ĐỐI TRỌNG ---
    cwt_cfg = next((c for c in crane['counterweight_configs'] if c['name'] == cwt_name), None)
    if not cwt_cfg: cwt_cfg = crane['counterweight_configs'][0]

    # --- B. LẮP GHÉP CẦN & TÍNH TOÁN VẬT LÝ ---
    boom_sys = crane['boom_system']
    
    # 1. Lắp ghép các đốt
    assembly = assemble_boom(boom_sys, target_boom_len)
    
    # 2. Tính khối lượng và CG chính xác
    real_boom_mass, real_boom_cg = calculate_boom_physics(assembly)
    
    # --- C. CÁC THÔNG SỐ KHÁC ---
    base = crane['base_structure']
    crawler = crane['crawler_system']
    
    # Khối lượng gầm tổng
    carbody_total = base['carbody_mass_ton'] + cwt_cfg.get('carbody_cwt_ton', 0.0) + \
                    (2 * crawler['track_mass_per_side_ton'])

    # --- D. ĐÓNG GÓI KẾT QUẢ ---
    specs = {
        # Định danh
        'id': crane_id,
        'model': crane['model_name'],
        
        # Geometry & Mass (Cho Physics Engine)
        'boom_len': assembly['total_len'],  # Chiều dài thực tế (sau khi lắp ghép)
        'boom_mass': real_boom_mass,        # Khối lượng thực tế (tổng các đốt)
        'boom_cg_radius': real_boom_cg,     # <--- THÔNG SỐ MỚI QUAN TRỌNG
        
        'upper_mass': base['upper_mass_ton'],
        'carbody_mass': carbody_total, 
        'cwt_mass': cwt_cfg['total_mass_ton'],
        'cwt_radius': cwt_cfg['radius_m'],
        
        'pivot_x': boom_sys['pivot_offset_x_m'],
        'pivot_z': boom_sys.get('pivot_offset_z_m', 1.5),
        'A_frame_h': 3.0, # Giá trị mặc định nếu JSON thiếu
        
        # Track Specs (Cho Mesh & Solver)
        'track_L': crawler['contact_length_m'],
        'track_W': crawler['shoe_width_m'],
        'track_gauge': crawler['track_gauge_m'],
        'track_area': crawler['contact_length_m'] * crawler['shoe_width_m']
    }
    return specs, None