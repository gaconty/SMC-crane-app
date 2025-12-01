import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crane_manager import CraneManager
from backend.crane_models import JibConfig

def test_jib_management():
    print("Testing Jib Management...")
    
    manager = CraneManager()
    
    # 1. Create a dummy crane
    crane_id = "TEST_CRANE_JIB"
    
    # Check if exists, delete if so
    if manager.get_crane(crane_id):
        manager.delete_crane(crane_id)
        
    # Get a base crane to copy (or create new if empty)
    cranes = manager.get_all_cranes()
    if not cranes:
        print("No cranes to copy from. Skipping.")
        return

    base_crane = cranes[0].copy()
    base_crane.id = crane_id
    base_crane.model_name = "Test Crane with Jib"
    
    # 2. Add Jib Configs
    jibs = [
        JibConfig(length_m=12.0, mass_ton=2.5, offset_angles=[10.0, 30.0]),
        JibConfig(length_m=18.0, mass_ton=3.8, offset_angles=[15.0, 45.0])
    ]
    base_crane.jib_configs = jibs
    
    # 3. Save
    print(f"Saving crane {crane_id} with {len(jibs)} jibs...")
    success = manager.add_crane(base_crane)
    
    if success:
        print("Save Success!")
    else:
        print("Save Failed!")
        return

    # 4. Retrieve and Verify
    loaded_crane = manager.get_crane(crane_id)
    if loaded_crane:
        print(f"Loaded Crane: {loaded_crane.model_name}")
        print(f"Jib Configs Found: {len(loaded_crane.jib_configs)}")
        
        for j in loaded_crane.jib_configs:
            print(f" - Jib {j.length_m}m, Mass {j.mass_ton}t, Offsets {j.offset_angles}")
            
        if len(loaded_crane.jib_configs) == 2:
            print("PASS: Jib count matches.")
        else:
            print("FAIL: Jib count mismatch.")
            
        # Clean up
        manager.delete_crane(crane_id)
        print("Cleaned up test crane.")
    else:
        print("FAIL: Could not load crane.")

if __name__ == "__main__":
    test_jib_management()
