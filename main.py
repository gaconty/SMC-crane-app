import sys
import os
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to sys.path to import core modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import core modules
try:
    from crane_physics import AdvancedCranePhysics
    from solver_engine import SoilStructureSolver
    from mesh_engine import AdvancedMeshGenerator
    # LoadMapper is imported inside SoilStructureSolver now, or we can import it here if needed
except ImportError as e:
    print(f"Error importing core modules: {e}")

from backend.models import CalculateInput, PhysicsResult, SolveInput, SolverResult

app = FastAPI(title="SMC Ground Pressure API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import json

@app.get("/")
def read_root():
    return {"message": "SMC Ground Pressure API is running"}

@app.get("/cranes")
def get_cranes():
    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "crane_data_library.json")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculate", response_model=PhysicsResult)
def calculate_physics(data: CalculateInput):
    try:
        # Initialize Physics Engine
        specs_dict = data.specs.dict()
        physics = AdvancedCranePhysics(specs_dict)
        
        # Run Calculation
        result = physics.calculate_state(
            load_mass=data.load_mass,
            boom_angle_deg=data.boom_angle_deg,
            slew_angle_deg=data.slew_angle_deg
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/solve", response_model=SolverResult)
def solve_ground_pressure(data: SolveInput):
    try:
        # Initialize Mesh
        mesh = AdvancedMeshGenerator(mesh_size=data.ground_specs.mesh_size)
        
        # Create a default rectangular mesh
        # We use create_rectangular_mesh for simplicity if available, or polygon
        # Let's assume a standard 20x20m ground for now
        mesh.create_rectangular_mesh(20.0, 20.0, default_Ks=data.ground_specs.default_Ks)
        
        # Initialize Solver
        # Note: SoilStructureSolver initializes LoadMapper internally if not passed
        solver = SoilStructureSolver(mesh)
        
        # Prepare Physics Result for Solver
        physics_res_dict = data.physics_result.dict()
        
        # Run Solver
        # solve_equilibrium(self, specs, physics_results, chassis_angle=0)
        result, error = solver.solve_equilibrium(
            specs=data.specs.dict(),
            physics_results=physics_res_dict,
            chassis_angle=data.chassis_angle
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
            
        return {
            "settlement_max": result["settlement_max"],
            "pressure_max": result["pressure_max"],
            "contact_ratio": result["contact_ratio"],
            "solver_iters": result["solver_iters"],
            "solver_status": result["solver_status"],
            "solver_cost": result["solver_cost"]
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
