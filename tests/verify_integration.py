import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agent import OfflineAIAgent

def test_integration():
    print("Testing Assistant AI + Learning AI Integration...")
    
    agent = OfflineAIAgent()
    
    if not agent.learner.is_trained:
        print("Model not trained yet. Please run verify_deep_ai.py first.")
        return

    # Test Smart Prediction
    # Use inputs similar to what we trained on
    load = 50.0
    radius = 12.0
    boom = 60.0
    angle = 0.0
    ks = 10000.0
    cwt = 30.0
    mat_L = 6.0
    mat_W = 0.8
    
    p_pred, err = agent.predict_pressure_smart(load, radius, boom, angle, ks, cwt, mat_L, mat_W)
    
    if p_pred is not None:
        print(f"Smart Prediction Success! P_max = {p_pred:.2f} t/m2")
    else:
        print(f"Smart Prediction Failed: {err}")

if __name__ == "__main__":
    test_integration()
