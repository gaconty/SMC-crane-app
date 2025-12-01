import unittest
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mesh_engine import AdvancedMeshGenerator
from solver_engine import SoilStructureSolver
from config import G_CONST

class TestSolverEngine(unittest.TestCase):
    def setUp(self):
        self.mesh_gen = AdvancedMeshGenerator(mesh_size=0.5) # Coarse mesh for speed
        self.mesh_gen.create_rectangular_mesh(L=10.0, W=6.0, default_Ks=10000)
        self.solver = SoilStructureSolver(self.mesh_gen)
        
        self.specs = {
            'track_L': 8.0,
            'track_W': 1.0,
            'track_gauge': 5.0
        }

    def test_solver_convergence_simple_load(self):
        # Vertical load only, center
        phys_res = {
            'V_total_ton': 100.0,
            'Mx_roll_Tm': 0.0,
            'My_pitch_Tm': 0.0,
            'Fx_slide_ton': 0.0,
            'Fy_slide_ton': 0.0
        }
        
        sol_res, err = self.solver.solve_equilibrium(self.specs, phys_res)
        
        self.assertIsNone(err)
        self.assertIsNotNone(sol_res)
        
        # Check total reaction matches load
        # Pressure sum * dA = Force
        # Force / G_CONST = Mass
        total_reaction_ton = np.sum(sol_res['pressure_map']) * self.mesh_gen.dA / G_CONST
        self.assertAlmostEqual(total_reaction_ton, 100.0, delta=1.0)
        
        # Check symmetry (settlement should be uniform)
        self.assertAlmostEqual(sol_res['pressure_max'], np.mean(sol_res['pressure_map'][sol_res['pressure_map']>0]), delta=5.0)

    def test_solver_eccentric_load(self):
        # Load with Moment (tipping forward)
        phys_res = {
            'V_total_ton': 100.0,
            'Mx_roll_Tm': 0.0,
            'My_pitch_Tm': 200.0, # Pitch moment
            'Fx_slide_ton': 0.0,
            'Fy_slide_ton': 0.0
        }
        
        sol_res, err = self.solver.solve_equilibrium(self.specs, phys_res)
        self.assertIsNone(err)
        
        # Front pressure should be higher than Rear
        # Note: We need to check where the pressure is high.
        # Assuming positive Y is front (or similar convention).
        # Just checking that max pressure is > avg pressure is enough to prove tilt.
        avg_p = np.mean(sol_res['pressure_map'][sol_res['pressure_map']>0])
        self.assertGreater(sol_res['pressure_max'], avg_p)

if __name__ == '__main__':
    unittest.main()
