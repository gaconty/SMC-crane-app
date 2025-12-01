import json
import os

file_path = r"e:\BẢNG TÍNH PRJ\SMC GROUND PRESSURE\crane_data_library.json"

def update_library():
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        updated_count = 0
        for crane in data.get("cranes", []):
            boom_sys = crane.get("boom_system", {})
            inserts = boom_sys.get("inserts", [])
            for insert in inserts:
                insert["quantity"] = 2
                updated_count += 1
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"Successfully updated {updated_count} inserts with quantity=2.")
        
    except Exception as e:
        print(f"Error updating file: {e}")

if __name__ == "__main__":
    update_library()
