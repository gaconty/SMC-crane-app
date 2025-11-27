import json
import os
import sys

# Định nghĩa tên file dữ liệu cẩu
DATA_FILE = "crane_data_library.json"

def load_data():
    """Tải dữ liệu cẩu hiện có từ file JSON."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Lỗi: File '{DATA_FILE}' bị lỗi cú pháp JSON. Bắt đầu với dữ liệu trống.")
            return {"cranes": []}
    else:
        return {"cranes": []}

def save_data(data):
    """Lưu dữ liệu cẩu vào file JSON."""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n[OK] Dữ liệu đã được lưu vào '{DATA_FILE}'")
    except Exception as e:
        print(f"\n[ERR] Lỗi khi lưu file: {e}")

def get_input(prompt, data_type=str, default_value=None):
    """Hàm nhập liệu chung, hỗ trợ giá trị mặc định."""
    while True:
        prompt_text = f"{prompt}"
        if default_value is not None:
            prompt_text += f" (Mặc định: {default_value})"
        
        user_input = input(f"{prompt_text}: ")
        
        if not user_input and default_value is not None:
            return default_value

        if data_type == str:
            if user_input.strip(): return user_input.strip()
        try:
            if data_type == float:
                return float(user_input.replace(',', '.'))
            if data_type == int:
                return int(user_input)
        except ValueError:
            print(f"  -> Lỗi: Vui lòng nhập số hợp lệ.")

def input_crane_details():
    """Thu thập thông tin chi tiết của một loại cẩu."""
    print("\n" + "="*50)
    print("NHẬP DỮ LIỆU CẨU MỚI")
    print("="*50)
    
    # --- PHẦN 1: THÔNG TIN CƠ BẢN ---
    print("\n[1] THÔNG TIN ĐỊNH DANH")
    crane_id = get_input("  ID Cẩu (viết liền, không dấu, vd: sany_scc800)", str)
    model_name = get_input("  Tên hiển thị (vd: SANY SCC800)", str)
    max_capacity_ton = get_input("  Sức nâng tối đa (Tấn)", float)

    # --- PHẦN 2: CẤU TRÚC GẦM ---
    print("\n[2] CẤU TRÚC GẦM & THÂN MÁY (BASE & CRAWLER)")
    upper_mass_ton = get_input("  Khối lượng bàn quay (Upper - Tấn)", float)
    carbody_mass_ton = get_input("  Khối lượng khung gầm xe (Carbody - Tấn)", float)
    
    print("  --- Hệ thống xích ---")
    track_mass_per_side_ton = get_input("  Khối lượng 1 bên dải xích (Tấn)", float)
    track_gauge_m = get_input("  Khoảng cách tâm 2 xích (Gauge - m)", float)
    contact_length_m = get_input("  Chiều dài tiếp xúc đất (m)", float)
    shoe_width_m = get_input("  Bề rộng bản xích (m)", float)

    # --- PHẦN 3: CẤU HÌNH CẦN (MODULAR BOOM) ---
    print("\n[3] HỆ THỐNG CẦN (BOOM MODULES)")
    print("  * Lưu ý: Hệ thống dùng cơ chế lắp ghép module.")
    
    pivot_offset_x_m = get_input("  Tọa độ chốt chân cần so với tâm quay (X - m)", float, default_value=0.0)
    pivot_offset_z_m = get_input("  Độ cao chốt chân cần so với mặt đất (Z - m)", float, default_value=1.5)
    
    # 3.1 Đốt Gốc
    print("\n  --- Đốt Gốc (Base Section) ---")
    base_len = get_input("  Chiều dài (m)", float)
    base_mass = get_input("  Khối lượng (Tấn)", float)
    base_cg = get_input("  Trọng tâm (% chiều dài, từ chốt)", float, default_value=0.45)

    # 3.2 Đốt Ngọn
    print("\n  --- Đốt Ngọn (Tip Section) ---")
    tip_len = get_input("  Chiều dài (m)", float)
    tip_mass = get_input("  Khối lượng (Tấn)", float)
    tip_cg = get_input("  Trọng tâm (% chiều dài, từ mối nối)", float, default_value=0.4)

    # 3.3 Đốt Giữa (Inserts)
    print("\n  --- Các loại Đốt Giữa (Inserts) ---")
    print("  (Nhập Enter tại ô ID để kết thúc nhập đốt giữa)")
    inserts_list = []
    
    while True:
        print(f"  > Đốt giữa #{len(inserts_list)+1}:")
        ins_id = input("    Mã đốt (vd: 3m, 6m, 12m) [Enter để xong]: ").strip()
        if not ins_id:
            if len(inserts_list) == 0:
                print("    [Cảnh báo] Bạn chưa nhập đốt giữa nào. Cẩu chỉ có Gốc + Ngọn?")
                confirm = input("    Tiếp tục? (y/n): ")
                if confirm.lower() != 'y': continue
            break
            
        ins_len = get_input("    Chiều dài (m)", float)
        ins_mass = get_input("    Khối lượng (Tấn)", float)
        # Inserts thường đối xứng nên CG mặc định 50%
        
        inserts_list.append({
            "id": ins_id,
            "length_m": ins_len,
            "mass_ton": ins_mass
        })
    
    # --- PHẦN 4: ĐỐI TRỌNG ---
    print("\n[4] CẤU HÌNH ĐỐI TRỌNG (COUNTERWEIGHT)")
    counterweight_configs = []
    while True:
        cwt_name = get_input("  Tên cấu hình (vd: Standard, Superlift, 40T)", str)
        cwt_mass = get_input("  Tổng tải đối trọng (Tấn)", float)
        cwt_radius = get_input("  Bán kính quay đuôi (m)", float)
        carbody_cwt = get_input("  Đối trọng gầm (Carbody CWT - Tấn)", float, default_value=0.0)
        
        counterweight_configs.append({
            "name": cwt_name,
            "total_mass_ton": cwt_mass,
            "radius_m": cwt_radius,
            "carbody_cwt_ton": carbody_cwt
        })
        
        more = input("  -> Thêm cấu hình khác? (y/n): ").strip().lower()
        if more != 'y': break

    # --- TỔNG HỢP JSON ---
    new_crane = {
        "id": crane_id,
        "model_name": model_name,
        "max_capacity_ton": max_capacity_ton,
        
        "base_structure": {
            "upper_mass_ton": upper_mass_ton,
            "carbody_mass_ton": carbody_mass_ton
        },

        "crawler_system": {
            "track_mass_per_side_ton": track_mass_per_side_ton,
            "contact_length_m": contact_length_m,
            "shoe_width_m": shoe_width_m,
            "track_gauge_m": track_gauge_m,
        },

        "counterweight_configs": counterweight_configs,

        # CẤU TRÚC BOOM MỚI
        "boom_system": {
            "pivot_offset_x_m": pivot_offset_x_m,
            "pivot_offset_z_m": pivot_offset_z_m,
            
            "base_section": {
                "length_m": base_len,
                "mass_ton": base_mass,
                "cg_percent": base_cg
            },
            "tip_section": {
                "length_m": tip_len,
                "mass_ton": tip_mass,
                "cg_percent": tip_cg
            },
            "inserts": inserts_list
        }
    }
    return new_crane

# --- CHƯƠNG TRÌNH CHÍNH ---
if __name__ == "__main__":
    data = load_data()
    
    try:
        new_crane_entry = input_crane_details()
    except KeyboardInterrupt:
        print("\n\n[INFO] Đã hủy nhập liệu.")
        sys.exit()

    # Kiểm tra trùng ID
    existing_ids = {c['id'] for c in data['cranes']}
    if new_crane_entry['id'] in existing_ids:
        print(f"\n[WARN] ID '{new_crane_entry['id']}' đã tồn tại!")
        overwrite = input("Bạn có muốn GHI ĐÈ không? (y/n): ").strip().lower()
        if overwrite == 'y':
            data['cranes'] = [c for c in data['cranes'] if c['id'] != new_crane_entry['id']]
            data['cranes'].append(new_crane_entry)
            save_data(data)
        else:
            print("[INFO] Đã hủy thao tác lưu.")
    else:
        data['cranes'].append(new_crane_entry)
        save_data(data)