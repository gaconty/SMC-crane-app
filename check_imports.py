import sys
import os

try:
    from crane_physics import AdvancedCranePhysics
    print("crane_physics: OK")
except Exception as e:
    print(f"crane_physics: FAILED - {e}")

try:
    from solver_engine import SoilStructureSolver
    print("solver_engine: OK")
except Exception as e:
    print(f"solver_engine: FAILED - {e}")

try:
    from mesh_engine import AdvancedMeshGenerator
    print("mesh_engine: OK")
except Exception as e:
    print(f"mesh_engine: FAILED - {e}")
