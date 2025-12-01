import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crane_physics import AdvancedCranePhysics
import numpy as np

def test_carbody_cwt():
    print("Testing Carbody Counterweight Physics...")
    
    # Mock Specs
    specs = {
        'track_L': 6.0, 'track_W': 0.8, 'track_gauge': 5.0,
        'carbody_mass': 10.0, 'carbody_cg_z': 0.8,
        'upper_mass': 30.0, 'upper_cg_z': 1.5,
        'pivot_x': 0.0, 'pivot_z': 1.8,
        'boom_len': 60.0, 'boom_mass': 12.0, 'boom_cg_radius': 24.0,
        'cwt_mass': 30.0, 'cwt_radius': 4.5, 'cwt_z': 1.2,
        'slope_y_pct': 0.0, 'angle_x': 0.0,
        'carbody_cwt_mass': 0.0 # Initially 0
    }
    
    physics = AdvancedCranePhysics(specs)
    load = 20.0
    boom_angle = 80.0
    slew = 0.0
    
    # 1. Without Carbody Cwt
    res_0 = physics.calculate_state(load, boom_angle, slew)
    print(f"Carbody Cwt 0t - V_total: {res_0['V_total_ton']:.2f} t")
    
    # 2. With Carbody Cwt 20t
    specs['carbody_cwt_mass'] = 20.0
    physics_20 = AdvancedCranePhysics(specs)
    res_20 = physics_20.calculate_state(load, boom_angle, slew)
    print(f"Carbody Cwt 20t - V_total: {res_20['V_total_ton']:.2f} t")
    
    # Checks
    diff = res_20['V_total_ton'] - res_0['V_total_ton']
    print(f"Difference: {diff:.2f} t")
    
    if abs(diff - 20.0) < 0.1:
        print("PASS: Total weight increased by exactly 20t.")
    else:
        print("FAIL: Total weight did not increase correctly.")

if __name__ == "__main__":
    test_carbody_cwt()
