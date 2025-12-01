from typing import List, Dict, Tuple
from itertools import combinations
from backend.crane_models import CraneData, BoomInsert

class BoomConfigResult:
    def __init__(self, total_len: float, total_mass: float, cg_radius: float, inserts_used: List[BoomInsert]):
        self.total_len = total_len
        self.total_mass = total_mass
        self.cg_radius = cg_radius
        self.inserts_used = inserts_used

def generate_boom_configs(crane: CraneData) -> Dict[float, BoomConfigResult]:
    """
    Generates all possible boom configurations based on available inserts.
    Returns a dict mapping {length: BoomConfigResult}.
    """
    base = crane.boom_system.base_section
    tip = crane.boom_system.tip_section
    available_inserts = []
    
    # Flatten inventory into a list of individual inserts
    for ins in crane.boom_system.inserts:
        qty = getattr(ins, 'quantity', 1)
        for _ in range(qty):
            available_inserts.append(ins)
            
    # Find all combinations
    # Since order doesn't matter for *existence* of a length, we just need combinations.
    # However, we need to handle duplicate inserts (same ID/specs).
    # To avoid duplicate calculations for identical lengths, we'll store by length.
    
    configs = {}
    
    # Base + Tip is the minimum config
    min_len = base.length_m + tip.length_m
    min_mass = base.mass_ton + tip.mass_ton
    
    # CG Calculation for Base + Tip
    # Moment = Base_Mass * Base_CG_Dist + Tip_Mass * Tip_CG_Dist
    # Base CG Dist from Pivot = Base_Len * Base_CG%
    # Tip CG Dist from Pivot = Base_Len + Tip_Len * Tip_CG% (Wait, Tip starts after Base?)
    # Actually, if no inserts: Tip starts at Base_Len.
    
    def calculate_config(inserts: List[BoomInsert]) -> BoomConfigResult:
        # Sort inserts: Shortest first (bottom) as per user rule
        sorted_inserts = sorted(inserts, key=lambda x: x.length_m)
        
        current_x = 0.0
        total_moment = 0.0
        total_mass = 0.0
        
        # 1. Base Section
        base_cg_dist = current_x + (base.length_m * base.cg_percent)
        total_moment += base.mass_ton * base_cg_dist
        total_mass += base.mass_ton
        current_x += base.length_m
        
        # 2. Inserts
        for ins in sorted_inserts:
            # Assume insert CG is in middle (0.5) unless specified? 
            # Models don't have CG for inserts, assuming uniform or 0.5
            ins_cg_dist = current_x + (ins.length_m * 0.5)
            total_moment += ins.mass_ton * ins_cg_dist
            total_mass += ins.mass_ton
            current_x += ins.length_m
            
        # 3. Tip Section
        tip_cg_dist = current_x + (tip.length_m * tip.cg_percent)
        total_moment += tip.mass_ton * tip_cg_dist
        total_mass += tip.mass_ton
        current_x += tip.length_m
        
        total_len = current_x
        cg_radius = total_moment / total_mass if total_mass > 0 else 0
        
        return BoomConfigResult(total_len, total_mass, cg_radius, sorted_inserts)

    # Add Base+Tip only
    configs[round(min_len, 2)] = calculate_config([])
    
    # Add combinations
    # Optimization: If we have many identical inserts, combinations() will produce duplicates.
    # But since N is small, we can just use set of indices or similar.
    # Better: Use recursion with counts.
    
    unique_lengths = {round(min_len, 2)}
    
    # Simple approach for small N: Iterate 1 to N items
    for r in range(1, len(available_inserts) + 1):
        for combo in combinations(available_inserts, r): 
            # set(combinations) works if objects are hashable. Pydantic models are not hashable by default unless frozen.
            # We can use IDs tuple to track uniqueness if needed, but let's just calculate and overwrite.
            # Actually, distinct insert objects with same values are distinct in list.
            # We care about the *sum of lengths*.
            
            res = calculate_config(list(combo))
            l_key = round(res.total_len, 2)
            
            # If multiple combos give same length, we usually pick the one with lighter mass?
            # Or just overwrite. Usually they are consistent.
            if l_key not in configs:
                configs[l_key] = res
                
    return configs
