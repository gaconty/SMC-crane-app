import json
import os
import math

CRANE_DATA_FILE = 'crane_data_library.json'

def load_full_database(file_path=CRANE_DATA_FILE):
    if not os.path.exists(file_path):
        return None, f"Không tìm thấy file: {file_path}"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {c['id']: c for c in data.get('cranes', [])}, None
    except Exception as e:
        return None, str(e)

def get_crane_options():
    db, msg = load_full_database()
    if not db: return None, msg
    options = {}
    for cid, data in db.items():
        configs = [cfg['name'] for cfg in data.get('counterweight_configs', [])]
        options[cid] = configs
    return options, None

def get_valid_boom_lengths(crane_id):
    db, _ = load_full_database()
    if not db or crane_id not in db: return []
    boom_sys = db[crane_id]['boom_system']
    min_len = boom_sys['base_section']['length_m'] + boom_sys['tip_section']['length_m']
    inserts = boom_sys.get('inserts', [])
    if not inserts: return [min_len]
    step = min(ins['length_m'] for ins in inserts)
    valid_lengths = []
    current = min_len
    while current <= 150.0:
        valid_lengths.append(current)
        current += step
    return valid_lengths

def assemble_boom(boom_sys, target_len):
    base = boom_sys['base_section']
    tip = boom_sys['tip_section']
    fixed_len = base['length_m'] + tip['length_m']
    needed_len = target_len - fixed_len
    available_inserts = sorted(boom_sys.get('inserts', []), key=lambda x: x['length_m'], reverse=True)
    chosen_inserts = []
    remaining = needed_len
    epsilon = 0.05 
    for ins in available_inserts:
        while remaining >= ins['length_m'] - epsilon:
            chosen_inserts.append(ins)
            remaining -= ins['length_m']
    return {
        "base": base, "tip": tip, "inserts": chosen_inserts,
        "total_len": fixed_len + sum(i['length_m'] for i in chosen_inserts)
    }

def calculate_boom_physics(assembly_config):
    base = assembly_config['base']
    tip = assembly_config['tip']
    inserts = assembly_config['inserts']
    
    total_mass = 0.0
    total_moment = 0.0
    current_x = 0.0 
    
    # Base
    m_base = base['mass_ton']
    cg_local = base['length_m'] * base.get('cg_percent', 0.5) 
    total_mass += m_base
    total_moment += m_base * (current_x + cg_local)
    current_x += base['length_m']
    
    # Inserts
    for ins in inserts:
        m_ins = ins['mass_ton']
        cg_global = current_x + (ins['length_m'] * 0.5)
        total_mass += m_ins
        total_moment += m_ins * cg_global
        current_x += ins['length_m']
        
    # Tip
    m_tip = tip['mass_ton']
    cg_local = tip['length_m'] * tip.get('cg_percent', 0.5)
    total_mass += m_tip
    total_moment += m_tip * (current_x + cg_local)
    
    cg_radius = total_moment / total_mass if total_mass > 0 else 0
    return total_mass, cg_radius

def get_processed_specs(crane_id, cwt_name, target_boom_len):
    db, msg = load_full_database()
    if not db or crane_id not in db: return None, "Không tìm thấy dữ liệu cẩu."
    crane = db[crane_id]
    
    cwt_cfg = next((c for c in crane['counterweight_configs'] if c['name'] == cwt_name), None)
    if not cwt_cfg: cwt_cfg = crane['counterweight_configs'][0]

    boom_sys = crane['boom_system']
    assembly = assemble_boom(boom_sys, target_boom_len)
    real_boom_mass, real_boom_cg = calculate_boom_physics(assembly)
    
    base = crane['base_structure']
    crawler = crane['crawler_system']
    
    carbody_total = base['carbody_mass_ton'] + cwt_cfg.get('carbody_cwt_ton', 0.0) + \
                    (2 * crawler['track_mass_per_side_ton'])

    specs = {
        'id': crane_id,
        'model': crane['model_name'],
        'boom_len': assembly['total_len'],
        'boom_mass': real_boom_mass,
        'boom_cg_radius': real_boom_cg,
        'upper_mass': base['upper_mass_ton'],
        
        # [PHASE A.2] NEW Z-Coordinates Inputs
        'upper_cg_z': base.get('cg_z_m', 1.5), 
        'carbody_cg_z': base.get('carbody_cg_z_m', 0.8),
        'cwt_z': cwt_cfg.get('z_m', 1.2),

        'carbody_mass': carbody_total, 
        'cwt_mass': cwt_cfg['total_mass_ton'],
        'cwt_radius': cwt_cfg['radius_m'],
        'pivot_x': boom_sys['pivot_offset_x_m'],
        'pivot_z': boom_sys.get('pivot_offset_z_m', 1.5),
        'A_frame_h': 3.0,
        'track_L': crawler['contact_length_m'],
        'track_W': crawler['shoe_width_m'],
        'track_gauge': crawler['track_gauge_m'],
        'track_area': crawler['contact_length_m'] * crawler['shoe_width_m'],
        
        # [PHASE A.2] Slope placeholders (will be filled by UI)
        'slope_grade_x_pct': 0.0,
        'slope_roll_y_pct': 0.0
    }
    return specs, None