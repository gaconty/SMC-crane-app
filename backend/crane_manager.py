import json
import os
from typing import List, Optional
from backend.crane_models import CraneData, CraneLibrary

class CraneManager:
    def __init__(self, data_file: str = "crane_data_library.json"):
        self.data_file = data_file
        self.library: CraneLibrary = self._load_data()

    def _load_data(self) -> CraneLibrary:
        """Loads crane data from the JSON file."""
        if not os.path.exists(self.data_file):
            # Return empty library if file doesn't exist
            return CraneLibrary(cranes=[])
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return CraneLibrary(**data)
        except Exception as e:
            print(f"Error loading crane data: {e}")
            return CraneLibrary(cranes=[])

    def save_data(self):
        """Saves the current library to the JSON file."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                # model_dump_json is for Pydantic v2, using dict() and json.dump for compatibility if needed
                # Assuming Pydantic v2 based on previous context, but let's be safe with json.dump
                # Use dict() and json.dumps for maximum compatibility across Pydantic versions
                f.write(json.dumps(self.library.dict(), indent=4, default=str))
        except Exception as e:
            print(f"Error saving crane data: {e}")

    def get_all_cranes(self) -> List[CraneData]:
        """Returns a list of all cranes."""
        return self.library.cranes

    def get_crane(self, crane_id: str) -> Optional[CraneData]:
        """Returns a specific crane by ID."""
        for crane in self.library.cranes:
            if crane.id == crane_id:
                return crane
        return None

    def add_crane(self, crane: CraneData) -> bool:
        """Adds a new crane. Returns True if successful, False if ID already exists."""
        if self.get_crane(crane.id):
            return False
        self.library.cranes.append(crane)
        self.save_data()
        return True

    def update_crane(self, crane_id: str, updated_crane: CraneData) -> bool:
        """Updates an existing crane. Returns True if successful."""
        for i, crane in enumerate(self.library.cranes):
            if crane.id == crane_id:
                # If ID is changed in updated_crane, check if new ID conflicts
                if crane_id != updated_crane.id and self.get_crane(updated_crane.id):
                    return False 
                
                self.library.cranes[i] = updated_crane
                self.save_data()
                return True
        return False

    def delete_crane(self, crane_id: str) -> bool:
        """Deletes a crane by ID. Returns True if successful."""
        initial_len = len(self.library.cranes)
        self.library.cranes = [c for c in self.library.cranes if c.id != crane_id]
        if len(self.library.cranes) < initial_len:
            self.save_data()
            return True
        return False
