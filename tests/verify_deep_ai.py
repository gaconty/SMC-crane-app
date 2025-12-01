import numpy as np
import random
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crane_physics import AdvancedCranePhysics
from solver_engine import SoilStructureSolver
from mesh_engine import AdvancedMeshGenerator
from backend.ai_learning import CraneAILearning

# Mock Specs
specs = {
    'boom_len': 60.0,
    'boom_cg_radius': 24.0,
    'pivot_x': 0.0,
    'pivot_z': 1.8,
    'carbody_mass': 10.0,
    'upper_mass': 30.0,
    'cwt_mass': 30.0,
    'boom_mass': 12.0,
    'cwt_radius': 4.5,
    'carbody_cg_z': 0.8,
    'upper_cg_z': 1.5,
    'cwt_z': 1.2,
    'track_L': 6.0,
    'track_W': 0.8,
    'track_gauge': 5.0,
    'slope_grade_x_pct': 0.0,
    'slope_roll_y_pct': 0.0
}

max_cap = 100.0
boom_len = 60.0
soil_ks = 10000.0
limit_pressure = 20.0

# Initialize Engines
physics_engine = AdvancedCranePhysics(specs)
mesh_gen = AdvancedMeshGenerator(mesh_size=0.5)
mesh_gen.create_rectangular_mesh(specs['track_L']*2.5, specs['track_gauge']*2.5, default_Ks=soil_ks)
solver = SoilStructureSolver(mesh_gen)
learner = CraneAILearning()

def run_deep_simulation():
    print("Starting Deep AI Simulation (360 deg, random load/radius)...")
    sim_angles = range(0, 360, 10) # Step 10 for test speed (36 iters)
    max_p_sim = 0
    valid_count = 0
    
    for i, ang in enumerate(sim_angles):
        # Generate Random Scenario
        sim_load = random.uniform(max_cap * 0.05, max_cap)
        sim_radius = random.uniform(3.0, boom_len * 0.7)
        
        # Calculate Physics
        sim_reach = min(sim_radius - specs['pivot_x'], boom_len * 0.99)
        sim_boom_angle = np.degrees(np.arccos(sim_reach/boom_len))
        
        p_res_sim = physics_engine.calculate_state(sim_load, sim_boom_angle, 90 - ang)
        
        # Sim Solver
        s_res_sim, err_sim = solver.solve_equilibrium(specs, p_res_sim)
        
        if not err_sim:
            p_val = s_res_sim['pressure_max'] / 9.81
            max_p_sim = max(max_p_sim, p_val)
            valid_count += 1
            
            # Log
            log_inputs = {
                'load_mass': sim_load, 'radius': sim_radius, 'boom_len': boom_len,
                'slew_angle': ang, 'soil_ks': soil_ks, 'cwt_mass': specs['cwt_mass'],
                'mat_L': specs['track_L'], 'mat_W': specs['track_W']
            }
            log_outputs = {'p_max': p_val, 'safety_factor': limit_pressure/p_val}
            learner.log_calculation(log_inputs, log_outputs)
            
            if i % 5 == 0:
                print(f"Iter {i}: Ang {ang}, Load {sim_load:.1f}, Rad {sim_radius:.1f} -> P_max {p_val:.2f}")
        else:
            print(f"Error at {ang}: {err_sim}")

    print(f"Simulation Complete. Valid: {valid_count}/{len(sim_angles)}. Max Pressure: {max_p_sim:.2f}")
    
    # Train
    msg = learner.train_model()
    print(msg)

if __name__ == "__main__":
    run_deep_simulation()
