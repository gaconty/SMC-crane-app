import numpy as np
from config import G_CONST, POLAR_RESOLUTION_DEG
from crane_physics import AdvancedCranePhysics
from mesh_engine import AdvancedMeshGenerator
from solver_engine import SoilStructureSolver
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_polar_profile(specs, load_mass, boom_angle, soil_ks, mat_config):
    """
    Calculate the maximum ground pressure for 360 degrees of slew.
    Optimized to use a coarser resolution defined in config.py.
    """
    logger.info(f"Starting Polar Analysis: Load={load_mass}t, Radius={specs.get('radius', 'N/A')}")
    
    # 1. Setup Simulation Environment (Reused for all angles)
    mesh_gen = AdvancedMeshGenerator(mesh_size=0.1) 
    L_sim = specs['track_L']
    
    # Adjust simulation area if mats are used
    if mat_config['use_left']: L_sim = max(L_sim, mat_config['L_left'])
    if mat_config['use_right']: L_sim = max(L_sim, mat_config['L_right'])
    
    # Create mesh once
    mesh_gen.create_rectangular_mesh(L_sim*2.2, specs['track_gauge']*2.2, default_Ks=soil_ks)
    solver = SoilStructureSolver(mesh_gen)
    physics_engine = AdvancedCranePhysics(specs)
    
    # Prepare solver specs
    solve_specs = specs.copy()
    if mat_config['use_left'] or mat_config['use_right']:
        solve_specs['track_L'] = L_sim
        solve_specs['track_W'] = max(specs['track_W'], mat_config.get('W_left',0), mat_config.get('W_right',0))
        
    # 2. Sweep Angles
    step = POLAR_RESOLUTION_DEG
    angles = np.arange(0, 360, step) 
    p_max_values = []
    
    for ang in angles:
        phys_angle = 90 - ang # Convert to Physics Coordinate System
        
        # Calculate Physics State
        phys_res = physics_engine.calculate_state(load_mass, boom_angle, phys_angle)
        
        # Solve Equilibrium
        sol_res, err = solver.solve_equilibrium(solve_specs, phys_res, chassis_angle=0)
        
        if sol_res:
            val = sol_res['pressure_max'] / G_CONST
        else:
            val = 0.0 # Solver failed (e.g. tipping)
            
        p_max_values.append(val)
        
    # 3. Close the loop for plotting
    angles = np.append(angles, 360)
    p_max_values = np.append(p_max_values, p_max_values[0])
    
    return angles, np.array(p_max_values)
