import numpy as np
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

load_mass = 50.0
radius = 12.0
boom_len = 60.0
soil_ks = 10000.0
limit_pressure = 20.0

# Calculate Boom Angle
reach = min(radius - specs['pivot_x'], boom_len * 0.99)
boom_angle = np.degrees(np.arccos(reach/boom_len))

# Initialize Engines
physics_engine = AdvancedCranePhysics(specs)
mesh_gen = AdvancedMeshGenerator(mesh_size=0.5) # Coarse mesh for speed
mesh_gen.create_rectangular_mesh(specs['track_L']*2.5, specs['track_gauge']*2.5, default_Ks=soil_ks)
solver = SoilStructureSolver(mesh_gen)
learner = CraneAILearning()

def run_simulation():
    print("Starting Auto AI Simulation...")
    sim_angles = range(0, 360, 45)
    max_p_sim = 0
    
    for i, ang in enumerate(sim_angles):
        print(f"Simulating Angle: {ang}")
        # Sim Physics
        p_res_sim = physics_engine.calculate_state(load_mass, boom_angle, 90 - ang)
        # Sim Solver
        s_res_sim, err_sim = solver.solve_equilibrium(specs, p_res_sim)
        
        if not err_sim:
            p_val = s_res_sim['pressure_max'] / 9.81 # Approx G_CONST
            max_p_sim = max(max_p_sim, p_val)
            
            # Log to AI
            log_inputs = {
                'load_mass': load_mass, 'radius': radius, 'boom_len': boom_len,
                'slew_angle': ang, 'soil_ks': soil_ks, 'cwt_mass': specs['cwt_mass']
            }
            log_outputs = {'p_max': p_val, 'safety_factor': limit_pressure/p_val}
            learner.log_calculation(log_inputs, log_outputs)
        else:
            print(f"Error at {ang}: {err_sim}")

    print(f"Simulation Complete. Max Pressure: {max_p_sim:.2f}")
    
    # Train
    msg = learner.train_model()
    print(msg)

if __name__ == "__main__":
    # Clean up old data for test
    if os.path.exists("calculation_history.csv"):
        # Keep it but maybe backup? For now just append is fine.
        pass
        
    run_simulation()
