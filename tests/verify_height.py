import numpy as np

def check_tip_height(pivot_z, boom_len, radius, pivot_x, load_height_z):
    reach = min(radius - pivot_x, boom_len * 0.99)
    boom_angle_rad = np.arccos(reach/boom_len)
    boom_angle_deg = np.degrees(boom_angle_rad)
    
    tip_height = pivot_z + boom_len * np.sin(boom_angle_rad)
    
    print(f"Boom Len: {boom_len}m, Radius: {radius}m")
    print(f"Boom Angle: {boom_angle_deg:.2f} deg")
    print(f"Tip Height: {tip_height:.2f}m")
    print(f"Required Height: {load_height_z}m")
    
    if tip_height < load_height_z:
        print("WARNING: Tip height too low!")
        return False
    else:
        print("OK: Height sufficient.")
        return True

if __name__ == "__main__":
    # Case 1: Sufficient height
    print("--- Case 1 ---")
    check_tip_height(pivot_z=1.8, boom_len=60, radius=20, pivot_x=0, load_height_z=30)
    
    # Case 2: Insufficient height
    print("\n--- Case 2 ---")
    check_tip_height(pivot_z=1.8, boom_len=60, radius=50, pivot_x=0, load_height_z=50)
