import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agent import OfflineAIAgent
from backend.crane_models import BaseStructure

def test_agents():
    print("Testing AI Agents (Optimizer & Safety)...")
    
    agent = OfflineAIAgent()
    
    # Mock Specs (Plain Dict to avoid Pydantic validation issues in test)
    base_specs = {
        'track_L': 6.0, 'track_W': 0.8, 'track_gauge': 5.0,
        'carbody_mass': 10.0, 'carbody_cg_z': 0.8,
        'upper_mass': 30.0, 'upper_cg_z': 1.5,
        'pivot_x': 0.0, 'pivot_z': 1.8,
        'boom_len': 60.0, 'boom_mass': 12.0, 'boom_cg_radius': 24.0,
        'cwt_mass': 30.0, 'cwt_radius': 4.5, 'cwt_z': 1.2
    }
    
    load = 50.0
    radius = 12.0
    boom_angle = 75.0
    slew_angle = 90.0
    soil_ks = 10000.0
    limit_p = 20.0
    
    # 1. Test Optimizer
    print("\n--- Testing Optimizer ---")
    if not agent.learner.is_trained:
        print("Warning: Learning AI not trained. Optimizer will be slow (Physics-based).")
    
    opt_res, err = agent.optimize_configuration(
        base_specs, load, radius, boom_angle, slew_angle, soil_ks, limit_p
    )
    
    if opt_res:
        print(f"Optimization Success! Best Mat: {opt_res['optimal_L']}x{opt_res['optimal_W']}")
    else:
        print(f"Optimization Failed: {err}")

    # 2. Test Safety Analysis
    print("\n--- Testing Safety Analysis ---")
    risk_res = agent.run_risk_analysis(
        base_specs, load, radius, boom_angle, slew_angle, soil_ks, limit_p, n_simulations=20
    )
    
    if risk_res:
        print(f"Risk Analysis Success! Failure Prob: {risk_res['failure_prob_pct']:.1f}%")
        print(f"Max Pressure (Mean): {risk_res['mean_p_max']:.2f}")
    else:
        print("Risk Analysis Failed.")

if __name__ == "__main__":
    test_agents()
