import unittest
import os
import json
from backend.crane_models import CraneData, BaseStructure, CrawlerSystem, CounterweightConfig, BoomSystem, BoomSection
from backend.crane_manager import CraneManager

class TestCraneManager(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_crane_library.json"
        # Create a dummy manager with a test file
        self.manager = CraneManager(data_file=self.test_file)
        
        # Create a sample crane object
        self.sample_crane = CraneData(
            id="TEST_CRANE_001",
            model_name="Test Crane 100T",
            max_capacity_ton=100.0,
            base_structure=BaseStructure(
                upper_mass_ton=30.0,
                carbody_mass_ton=10.0
            ),
            crawler_system=CrawlerSystem(
                track_mass_per_side_ton=15.0,
                contact_length_m=6.0,
                shoe_width_m=1.0,
                track_gauge_m=5.0
            ),
            counterweight_configs=[
                CounterweightConfig(
                    name="Standard 40t",
                    total_mass_ton=40.0,
                    radius_m=5.0
                )
            ],
            boom_system=BoomSystem(
                pivot_offset_x_m=1.0,
                pivot_offset_z_m=2.0,
                base_section=BoomSection(length_m=6.0, mass_ton=2.0),
                tip_section=BoomSection(length_m=6.0, mass_ton=1.5),
                inserts=[]
            )
        )

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_add_and_get_crane(self):
        # Test Add
        success = self.manager.add_crane(self.sample_crane)
        self.assertTrue(success)
        
        # Test Get
        crane = self.manager.get_crane("TEST_CRANE_001")
        self.assertIsNotNone(crane)
        self.assertEqual(crane.model_name, "Test Crane 100T")

    def test_add_duplicate_fail(self):
        self.manager.add_crane(self.sample_crane)
        success = self.manager.add_crane(self.sample_crane)
        self.assertFalse(success)

    def test_update_crane(self):
        self.manager.add_crane(self.sample_crane)
        
        # Modify
        updated_crane = self.sample_crane.model_copy(deep=True)
        updated_crane.model_name = "Updated Name"
        
        success = self.manager.update_crane("TEST_CRANE_001", updated_crane)
        self.assertTrue(success)
        
        # Verify
        crane = self.manager.get_crane("TEST_CRANE_001")
        self.assertEqual(crane.model_name, "Updated Name")

    def test_delete_crane(self):
        self.manager.add_crane(self.sample_crane)
        
        success = self.manager.delete_crane("TEST_CRANE_001")
        self.assertTrue(success)
        
        crane = self.manager.get_crane("TEST_CRANE_001")
        self.assertNone(crane)

if __name__ == '__main__':
    unittest.main()
