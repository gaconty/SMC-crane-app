import json
import os
import sys

DATA_FILE = "crane_data_library.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"cranes": []}
    return {"cranes": []}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n[OK] Dữ liệu đã được lưu vào '{DATA_FILE}'")
    except Exception as e:
        print(f"\n[ERR] Lỗi khi lưu file: {e}")

def get_input(prompt, data_type=str, default_value=None):
    while True:
        prompt_text = f"{prompt}"
        if default_value is not None:
            prompt_text += f" (Mặc định: {default_value})"
        user_input = input(f"{prompt_text}: ")
        if not user_input and default_value is not None:
            return default_value
        if data_type == str:
            if user_input.strip(): return user_input.strip()
    carbody_mass_ton = get_input("  Khối lượng khung gầm xe (Carbody - Tấn)", float)
    # NEW: Input Z for Carbody
    carbody_z_m = get_input("  [MỚI] Cao độ trọng tâm gầm (Z - m)", float, default_value=0.8)
    
    track_mass_per_side_ton = get_input("  Khối lượng 1 bên dải xích (Tấn)", float)
    track_gauge_m = get_input("  Khoảng cách tâm 2 xích (Gauge - m)", float)
    contact_length_m = get_input("  Chiều dài tiếp xúc đất (m)", float)
    shoe_width_m = get_input("  Bề rộng bản xích (m)", float)

    print("\n[3] HỆ THỐNG CẦN (BOOM MODULES)")
    pivot_offset_x_m = get_input("  Tọa độ chốt chân cần (X - m)", float, default_value=0.0)
    pivot_offset_z_m = get_input("  Độ cao chốt chân cần (Z - m)", float, default_value=1.5)
    
    base_len = get_input("  Chiều dài Đốt Gốc (m)", float)
    base_mass = get_input("  Khối lượng Đốt Gốc (Tấn)", float)
    base_cg = get_input("  Trọng tâm Đốt Gốc (%)", float, default_value=0.45)

    tip_len = get_input("  Chiều dài Đốt Ngọn (m)", float)
    tip_mass = get_input("  Khối lượng Đốt Ngọn (Tấn)", float)
    tip_cg = get_input("  Trọng tâm Đốt Ngọn (%)", float, default_value=0.4)

    inserts_list = []
    print("\n  --- Các loại Đốt Giữa (Inserts) ---")
    while True:
        ins_id = input("    Mã đốt (Enter để xong): ").strip()
        if not ins_id: break
        ins_len = get_input("    Chiều dài (m)", float)
        ins_mass = get_input("    Khối lượng (Tấn)", float)
        inserts_list.append({"id": ins_id, "length_m": ins_len, "mass_ton": ins_mass})
    
    print("\n[4] CẤU HÌNH ĐỐI TRỌNG")
    counterweight_configs = []
    while True:
        cwt_name = get_input("  Tên cấu hình", str)
        cwt_mass = get_input("  Tổng tải đối trọng (Tấn)", float)
        cwt_radius = get_input("  Bán kính quay đuôi (m)", float)
        # NEW: Input Z for CWT
        cwt_z = get_input("  [MỚI] Cao độ trọng tâm đối trọng (Z - m)", float, default_value=1.2)
        carbody_cwt = get_input("  Đối trọng gầm (Tấn)", float, default_value=0.0)
        
        counterweight_configs.append({
            "name": cwt_name,
            "total_mass_ton": cwt_mass,
            "radius_m": cwt_radius,
            "z_m": cwt_z, # Lưu giá trị mới
            "carbody_cwt_ton": carbody_cwt
        })
        if input("  -> Thêm cấu hình khác? (y/n): ").strip().lower() != 'y': break

    new_crane = {
        "id": crane_id,
        "model_name": model_name,
        "max_capacity_ton": max_capacity_ton,
        "base_structure": {
            "upper_mass_ton": upper_mass_ton,
            "cg_z_m": upper_z_m, # NEW
            "carbody_mass_ton": carbody_mass_ton,
            "carbody_cg_z_m": carbody_z_m # NEW
        },
        "crawler_system": {
            "track_mass_per_side_ton": track_mass_per_side_ton,
            "contact_length_m": contact_length_m,
            "shoe_width_m": shoe_width_m,
            "track_gauge_m": track_gauge_m,
        },
        "counterweight_configs": counterweight_configs,
        "boom_system": {
            "pivot_offset_x_m": pivot_offset_x_m,
            "pivot_offset_z_m": pivot_offset_z_m,
            "base_section": {"length_m": base_len, "mass_ton": base_mass, "cg_percent": base_cg},
            "tip_section": {"length_m": tip_len, "mass_ton": tip_mass, "cg_percent": tip_cg},
            "inserts": inserts_list
import json
import os
import sys

DATA_FILE = "crane_data_library.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"cranes": []}
    return {"cranes": []}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"\n[OK] Dữ liệu đã được lưu vào '{DATA_FILE}'")
    except Exception as e:
        print(f"\n[ERR] Lỗi khi lưu file: {e}")

def get_input(prompt, data_type=str, default_value=None):
    while True:
        prompt_text = f"{prompt}"
        if default_value is not None:
            prompt_text += f" (Mặc định: {default_value})"
        user_input = input(f"{prompt_text}: ")
        if not user_input and default_value is not None:
            return default_value
        if data_type == str:
            if user_input.strip(): return user_input.strip()
    carbody_mass_ton = get_input("  Khối lượng khung gầm xe (Carbody - Tấn)", float)
    # NEW: Input Z for Carbody
    carbody_z_m = get_input("  [MỚI] Cao độ trọng tâm gầm (Z - m)", float, default_value=0.8)
    
    track_mass_per_side_ton = get_input("  Khối lượng 1 bên dải xích (Tấn)", float)
    track_gauge_m = get_input("  Khoảng cách tâm 2 xích (Gauge - m)", float)
    contact_length_m = get_input("  Chiều dài tiếp xúc đất (m)", float)
    shoe_width_m = get_input("  Bề rộng bản xích (m)", float)

    print("\n[3] HỆ THỐNG CẦN (BOOM MODULES)")
    pivot_offset_x_m = get_input("  Tọa độ chốt chân cần (X - m)", float, default_value=0.0)
    pivot_offset_z_m = get_input("  Độ cao chốt chân cần (Z - m)", float, default_value=1.5)
    
    base_len = get_input("  Chiều dài Đốt Gốc (m)", float)
    base_mass = get_input("  Khối lượng Đốt Gốc (Tấn)", float)
    base_cg = get_input("  Trọng tâm Đốt Gốc (%)", float, default_value=0.45)

    tip_len = get_input("  Chiều dài Đốt Ngọn (m)", float)
    tip_mass = get_input("  Khối lượng Đốt Ngọn (Tấn)", float)
    tip_cg = get_input("  Trọng tâm Đốt Ngọn (%)", float, default_value=0.4)

    inserts_list = []
    print("\n  --- Các loại Đốt Giữa (Inserts) ---")
    while True:
        ins_id = input("    Mã đốt (Enter để xong): ").strip()
        if not ins_id: break
        ins_len = get_input("    Chiều dài (m)", float)
        ins_mass = get_input("    Khối lượng (Tấn)", float)
        inserts_list.append({"id": ins_id, "length_m": ins_len, "mass_ton": ins_mass})
    
    print("\n[4] CẤU HÌNH ĐỐI TRỌNG")
    counterweight_configs = []
    while True:
        cwt_name = get_input("  Tên cấu hình", str)
        cwt_mass = get_input("  Tổng tải đối trọng (Tấn)", float)
        cwt_radius = get_input("  Bán kính quay đuôi (m)", float)
        # NEW: Input Z for CWT
        cwt_z = get_input("  [MỚI] Cao độ trọng tâm đối trọng (Z - m)", float, default_value=1.2)
        carbody_cwt = get_input("  Đối trọng gầm (Tấn)", float, default_value=0.0)
        
        counterweight_configs.append({
            "name": cwt_name,
            "total_mass_ton": cwt_mass,
            "radius_m": cwt_radius,
            "z_m": cwt_z, # Lưu giá trị mới
            "carbody_cwt_ton": carbody_cwt
        })
        if input("  -> Thêm cấu hình khác? (y/n): ").strip().lower() != 'y': break

    new_crane = {
        "id": crane_id,
        "model_name": model_name,
        "max_capacity_ton": max_capacity_ton,
        "base_structure": {
            "upper_mass_ton": upper_mass_ton,
            "cg_z_m": upper_z_m, # NEW
            "carbody_mass_ton": carbody_mass_ton,
            "carbody_cg_z_m": carbody_z_m # NEW
        },
        "crawler_system": {
            "track_mass_per_side_ton": track_mass_per_side_ton,
            "contact_length_m": contact_length_m,
            "shoe_width_m": shoe_width_m,
            "track_gauge_m": track_gauge_m,
        },
        "counterweight_configs": counterweight_configs,
        "boom_system": {
            "pivot_offset_x_m": pivot_offset_x_m,
            "pivot_offset_z_m": pivot_offset_z_m,
            "base_section": {"length_m": base_len, "mass_ton": base_mass, "cg_percent": base_cg},
            "tip_section": {"length_m": tip_len, "mass_ton": tip_mass, "cg_percent": tip_cg},
            "inserts": inserts_list
        }
    }
    return new_crane

if __name__ == "__main__":
    data = load_data()
    try:
        new_crane_entry = input_crane_details(data)
        data['cranes'] = [c for c in data['cranes'] if c['id'] != new_crane_entry['id']]
        data['cranes'].append(new_crane_entry)
        save_data(data)
    except KeyboardInterrupt:
        sys.exit()