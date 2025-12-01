from backend.crane_models import CounterweightConfig

def test_counterweight_config():
    # Test default
    cwt = CounterweightConfig(name="Test", total_mass_ton=10, radius_m=5)
    print(f"Default carbody_cwt_ton: {cwt.carbody_cwt_ton}")
    assert cwt.carbody_cwt_ton == 0.0

    # Test with value
    cwt_custom = CounterweightConfig(name="Test", total_mass_ton=10, radius_m=5, carbody_cwt_ton=5.5)
    print(f"Custom carbody_cwt_ton: {cwt_custom.carbody_cwt_ton}")
    assert cwt_custom.carbody_cwt_ton == 5.5

    print("Verification Successful!")

if __name__ == "__main__":
    test_counterweight_config()
