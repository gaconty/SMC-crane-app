import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as patches

def draw_pressure_profile_visual(specs, sol_res, mat_config, limit_pressure, mesh_gen, slew_angle):
    """
    Vẽ bản đồ áp lực và tính toán các thông số thống kê.
    """
    pressure_map = sol_res['pressure_map']
    X = mesh_gen.nodes_X
    Y = mesh_gen.nodes_Y
    dA = mesh_gen.dA
    
    # Setup figure
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Plot contour
    # Use a custom cmap or standard 'jet'/'viridis'
    cmap = plt.cm.jet
    contour = ax.contourf(X, Y, pressure_map, levels=20, cmap=cmap)
    cbar = plt.colorbar(contour, ax=ax, label='Áp lực (t/m²)')
    
    # Draw tracks
    track_L = specs['track_L']
    track_W = specs['track_W']
    gauge = specs['track_gauge']
    
    # Left Track
    rect_L = patches.Rectangle((-track_L/2, gauge/2 - track_W/2), track_L, track_W, 
                               linewidth=1, edgecolor='black', facecolor='none', linestyle='--')
    ax.add_patch(rect_L)
    
    # Right Track
    rect_R = patches.Rectangle((-track_L/2, -gauge/2 - track_W/2), track_L, track_W, 
                               linewidth=1, edgecolor='black', facecolor='none', linestyle='--')
    ax.add_patch(rect_R)
    
    # Draw Mats if active
    if mat_config.get('use_left'):
        mL = mat_config['L_left']
        mW = mat_config['W_left']
        rect_mL = patches.Rectangle((-mL/2, gauge/2 - mW/2), mL, mW, 
                                   linewidth=2, edgecolor='blue', facecolor='none', label='Mat Left')
        ax.add_patch(rect_mL)

    if mat_config.get('use_right'):
        mR = mat_config['L_right']
        mW = mat_config['W_right']
        rect_mR = patches.Rectangle((-mR/2, -gauge/2 - mW/2), mR, mW, 
                                   linewidth=2, edgecolor='blue', facecolor='none', label='Mat Right')
        ax.add_patch(rect_mR)

    # Calculate Stats
    # Mask for Left and Right tracks (approximate based on Y coordinates)
    mask_L = Y > 0
    mask_R = Y < 0
    
    p_L = pressure_map[mask_L]
    p_R = pressure_map[mask_R]
    
    # Load (Tons) = Sum(Pressure * Area)
    lL = np.sum(p_L) * dA
    lR = np.sum(p_R) * dA
    
    # Effective Length (approximate)
    # Count nodes with pressure > 0 along the track length
    # This is a simplification. A better way is to project to X axis.
    # For now, let's use the ratio of active nodes to total nodes in the track area * track length
    # But we don't have the exact track mask here easily without re-calculating.
    # Let's use the contact ratio from sol_res if available, or estimate.
    # sol_res has 'contact_ratio' but it's global.
    
    # Estimate based on X range of active pressure
    if np.any(p_L > 1e-3):
        x_L = X[mask_L][p_L > 1e-3]
        eL = np.max(x_L) - np.min(x_L)
    else:
        eL = 0.0
        
    if np.any(p_R > 1e-3):
        x_R = X[mask_R][p_R > 1e-3]
        eR = np.max(x_R) - np.min(x_R)
    else:
        eR = 0.0
        
    # Efficiency
    pct_L = (eL / track_L) * 100 if track_L > 0 else 0
    pct_R = (eR / track_L) * 100 if track_L > 0 else 0
    
    # Corners
    # Find pressure at 4 corners of the tracks
    # FL: Front Left (Max X, Pos Y)
    # FR: Front Right (Max X, Neg Y)
    # RL: Rear Left (Min X, Pos Y)
    # RR: Rear Right (Min X, Neg Y)
    
    def get_pressure_at(x, y):
        # Find nearest node
        dist = (X - x)**2 + (Y - y)**2
        idx = np.unravel_index(np.argmin(dist), dist.shape)
        return pressure_map[idx]

    corners = {
        'FL': get_pressure_at(track_L/2, gauge/2),
        'FR': get_pressure_at(track_L/2, -gauge/2),
        'RL': get_pressure_at(-track_L/2, gauge/2),
        'RR': get_pressure_at(-track_L/2, -gauge/2)
    }

    ax.set_title(f"Ground Pressure Map (Slew: {slew_angle}°)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.axis('equal')
    
    return fig, lL, lR, eL, eR, pct_L, pct_R, corners

def draw_polar_chart_pro(angles, vals, slew_angle, limit_pressure):
    """
    Vẽ biểu đồ cực thể hiện áp lực/ổn định theo góc quay.
    """
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    
    # Convert angles to radians
    theta = np.radians(angles)
    
    # Plot limit line
    ax.plot(theta, [limit_pressure]*len(theta), 'r--', label='Limit')
    
    # Plot actual values
    ax.plot(theta, vals, 'b-', linewidth=2, label='Pressure')
    ax.fill(theta, vals, 'b', alpha=0.1)
    
    # Highlight current slew angle
    current_rad = np.radians(slew_angle)
    # Find value at current angle (approx)
    # Assuming angles are sorted
    idx = np.argmin(np.abs(angles - slew_angle))
    current_val = vals[idx]
    
    ax.plot([current_rad], [current_val], 'ro', markersize=10)
    ax.annotate(f"{slew_angle}°", xy=(current_rad, current_val), xytext=(10, 10), textcoords='offset points')
    
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title("Stability / Pressure Polar Chart")
    ax.legend()
    
    return fig
