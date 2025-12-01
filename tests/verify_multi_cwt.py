from backend.crane_models import CraneData, CounterweightConfig, BaseStructure, CrawlerSystem, BoomSystem, BoomSection

def test_multiple_cwts():
    # Create multiple configs
    cwt1 = CounterweightConfig(name="Standard", total_mass_ton=30, radius_m=5, carbody_cwt_ton=0)
    cwt2 = CounterweightConfig(name="Superlift", total_mass_ton=100, radius_m=10, carbody_cwt_ton=20)
    
    # Create CraneData with these configs
    crane = CraneData(
        id="TEST_001",
        model_name="Test Crane",
        max_capacity_ton=100,
        base_structure=BaseStructure(upper_mass_ton=10, carbody_mass_ton=10),
        crawler_system=CrawlerSystem(track_mass_per_side_ton=5, contact_length_m=5, shoe_width_m=1, track_gauge_m=5),
        counterweight_configs=[cwt1, cwt2],
        boom_system=BoomSystem(
            pivot_offset_x_m=0, pivot_offset_z_m=0,
            base_section=BoomSection(length_m=5, mass_ton=1),
            tip_section=BoomSection(length_m=5, mass_ton=1)
        )
    )
    
    print(f"Number of CWT configs: {len(crane.counterweight_configs)}")
    assert len(crane.counterweight_configs) == 2
    assert crane.counterweight_configs[0].name == "Standard"
    assert crane.counterweight_configs[1].name == "Superlift"
    assert crane.counterweight_configs[1].carbody_cwt_ton == 20.0
    
    print("Verification Successful!")

if __name__ == "__main__":
    test_multiple_cwts()
