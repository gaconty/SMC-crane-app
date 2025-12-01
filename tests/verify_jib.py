import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crane_physics import AdvancedCranePhysics
import numpy as np

def test_jib_physics():
    print("Testing Fixed Jib Physics...")
    
    # Mock Specs
    specs = {
        'track_L': 6.0, 'track_W': 0.8, 'track_gauge': 5.0,
        'carbody_mass': 10.0, 'carbody_cg_z': 0.8,
        'upper_mass': 30.0, 'upper_cg_z': 1.5,
        'pivot_x': 0.0, 'pivot_z': 1.8,
        'boom_len': 60.0, 'boom_mass': 12.0, 'boom_cg_radius': 24.0,
        'cwt_mass': 30.0, 'cwt_radius': 4.5, 'cwt_z': 1.2,
        'slope_y_pct': 0.0, 'angle_x': 0.0
    }
    
    physics = AdvancedCranePhysics(specs)
    load = 20.0
    boom_angle = 80.0
    slew = 0.0
    
    # 1. Without Jib
    res_no_jib = physics.calculate_state(load, boom_angle, slew)
    print(f"No Jib - Moment (Pitch): {res_no_jib['My_pitch_Tm']:.2f} Tm, Tip Height: {res_no_jib['tip_height']:.2f} m")
    
    # 2. With Jib (12m, 10 deg offset)
    jib_len = 12.0
    jib_offset = 10.0
    jib_mass = 2.4
    
    res_jib = physics.calculate_state(load, boom_angle, slew, jib_length=jib_len, jib_offset_deg=jib_offset, jib_mass=jib_mass)
    print(f"With Jib - Moment (Pitch): {res_jib['My_pitch_Tm']:.2f} Tm, Tip Height: {res_jib['tip_height']:.2f} m")
    
    # Checks (Note: Moment might be negative depending on coordinate system, check magnitude)
    if abs(res_jib['My_pitch_Tm']) > abs(res_no_jib['My_pitch_Tm']):
        print("PASS: Moment magnitude increased with Jib.")
    else:
        print("FAIL: Moment magnitude did not increase.")
        
    if res_jib['tip_height'] > res_no_jib['tip_height']:
        print("PASS: Tip Height increased with Jib.")
    else:
        print("FAIL: Tip Height did not increase.")

if __name__ == "__main__":
    test_jib_physics()
