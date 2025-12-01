import requests
import json
import time
import subprocess
import sys

# Start the server in a separate process if not running
# But for this test script, we assume the user/agent starts it.
# However, I can try to hit it.

BASE_URL = "http://localhost:8000"

def test_calculate():
    print("Testing /calculate...")
    payload = {
        "load_mass": 50.0,
        "boom_angle_deg": 60.0,
        "slew_angle_deg": 0.0,
        "specs": {
            "boom_len": 30.0,
            "boom_cg_radius": 12.0,
            "pivot_x": 0.0,
            "pivot_z": 1.5,
            "carbody_mass": 20.0,
            "upper_mass": 15.0,
            "cwt_mass": 10.0,
            "boom_mass": 5.0,
            "cwt_radius": 4.0,
            "track_L": 6.0,
            "track_W": 0.8,
            "track_gauge": 4.0
        }
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/calculate", json=payload)
        if resp.status_code == 200:
            print("SUCCESS: /calculate")
            return resp.json(), payload["specs"]
        else:
            print(f"FAILED: /calculate {resp.status_code} {resp.text}")
            return None, None
    except Exception as e:
        print(f"ERROR: {e}")
        return None, None

def test_solve(physics_res, specs):
    print("Testing /solve...")
    payload = {
        "physics_result": physics_res,
        "specs": specs,
        "ground_specs": {
            "mesh_size": 0.5,
            "default_Ks": 5000.0
        },
        "chassis_angle": 0.0
    }
    
    try:
        resp = requests.post(f"{BASE_URL}/solve", json=payload)
        if resp.status_code == 200:
            print("SUCCESS: /solve")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"FAILED: /solve {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    # Wait a bit for server to start if we just launched it
    time.sleep(2)
    
    phys_res, specs = test_calculate()
    if phys_res:
        test_solve(phys_res, specs)
