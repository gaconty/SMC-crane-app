from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class CraneSpecs(BaseModel):
    # Basic specs needed for CranePhysics
    boom_len: float
    boom_cg_radius: float
    pivot_x: float
    pivot_z: float
    carbody_mass: float
    upper_mass: float
    cwt_mass: float
    boom_mass: float
    cwt_radius: float
    # Optional/Defaulted specs
    carbody_cg_z: float = 0.8
    upper_cg_z: float = 1.5
    cwt_z: float = 1.2
    
    # Specs for Solver/LoadMapper
    track_L: float
    track_W: float
    track_gauge: float
    mat_L: Optional[float] = None
    mat_W: Optional[float] = None

class GroundSpecs(BaseModel):
    # Simplified ground specs for now
    # In future this might include polygon vertices
    mesh_size: float = 0.5
    default_Ks: float = 5000.0
    
class CalculateInput(BaseModel):
    load_mass: float
    boom_angle_deg: float
    slew_angle_deg: float
    specs: CraneSpecs

class PhysicsResult(BaseModel):
    V_total_ton: float
    Mx_roll_Tm: float
    My_pitch_Tm: float
    Mz_yaw_Tm: float
    Fx_slide_ton: float
    Fy_slide_ton: float
    geom_radius: float
    tip_pos_world: List[float]

class SolveInput(BaseModel):
    physics_result: PhysicsResult
    specs: CraneSpecs
    ground_specs: GroundSpecs
    chassis_angle: float = 0.0

class SolverResult(BaseModel):
    settlement_max: float
    pressure_max: float
    contact_ratio: float
    solver_iters: int
    solver_status: int
    solver_cost: float
    # We might not want to send the full pressure map every time if it's huge, 
    # but for now let's include it or a simplified version.
    # pressure_map: List[List[float]] # This might be 2D array flattened or similar
