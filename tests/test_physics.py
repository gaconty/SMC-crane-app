import unittest
import numpy as np
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crane_physics import AdvancedCranePhysics
from config import G_CONST

class TestCranePhysics(unittest.TestCase):
    def setUp(self):
        self.specs = {
            'id': 'TEST_CRANE',
            'model': 'Test Model',
            'boom_len': 60.0,
            'boom_mass': 10.0,
            'boom_cg_radius': 30.0,
            'upper_mass': 20.0,
            'upper_cg_z': 1.5,
            'carbody_mass': 30.0,
            'carbody_cg_z': 0.8,
            'cwt_mass': 50.0,
            'cwt_radius': 6.0,
            'cwt_z': 1.2,
            'pivot_x': 1.5,
            'pivot_z': 2.0,
            'slope_grade_x_pct': 0.0,
            'slope_roll_y_pct': 0.0
        }
        self.physics = AdvancedCranePhysics(self.specs)

    def test_initialization(self):
        self.assertIsNotNone(self.physics)
        self.assertAlmostEqual(self.physics.g_mag, G_CONST)

    def test_static_load_zero_angle(self):
        # Test at 0 degree slew (Front)
        res = self.physics.calculate_state(load_mass=10.0, boom_angle_deg=80.0, slew_angle_deg=0.0)
        
        # Check Total Vertical Load
        # Total = Boom + Upper + Carbody + Cwt + Load
        expected_mass = 10 + 20 + 30 + 50 + 10
        self.assertAlmostEqual(res['V_total_ton'], expected_mass, places=2)
        
        # Check Symmetry (My_pitch should be significant, Mx_roll should be ~0)
        self.assertAlmostEqual(res['Mx_roll_Tm'], 0.0, places=2)
        self.assertNotEqual(res['My_pitch_Tm'], 0.0)

    def test_slew_90_degrees(self):
        # Test at 90 degree slew (Side)
        res = self.physics.calculate_state(load_mass=10.0, boom_angle_deg=80.0, slew_angle_deg=90.0)
        
        # Mx_roll should be significant now (Side moment)
        self.assertNotEqual(res['Mx_roll_Tm'], 0.0)
        # My_pitch should be small (only from carbody/slope if any)
        # Note: Carbody is static, but Upper rotates. 
        
    def test_slope_effect(self):
        # Add slope
        self.specs['slope_grade_x_pct'] = 5.0
        physics_slope = AdvancedCranePhysics(self.specs)
        res = physics_slope.calculate_state(load_mass=10.0, boom_angle_deg=80.0, slew_angle_deg=0.0)
        
        # Sliding force should exist
        self.assertNotEqual(res['Fx_slide_ton'], 0.0)

if __name__ == '__main__':
    unittest.main()
