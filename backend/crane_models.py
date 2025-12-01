from pydantic import BaseModel, Field
from typing import List, Optional

class BaseStructure(BaseModel):
    upper_mass_ton: float = Field(..., description="Mass of the upper structure")
    carbody_mass_ton: float = Field(..., description="Mass of the carbody")
    carbody_cg_z_m: float = Field(0.8, description="Vertical CG of carbody")
    upper_cg_z_m: float = Field(2.2, description="Vertical CG of upper structure")

class CrawlerSystem(BaseModel):
    track_mass_per_side_ton: float
    contact_length_m: float
    shoe_width_m: float
    track_gauge_m: float

class CounterweightConfig(BaseModel):
    name: str
    total_mass_ton: float
    radius_m: float
    carbody_cwt_ton: float = 0.0
    cwt_z_m: float = 2.5 # Default height

class BoomSection(BaseModel):
    length_m: float
    mass_ton: float
    cg_percent: float = 0.5

class BoomInsert(BaseModel):
    id: str
    length_m: float
    mass_ton: float
    quantity: int = 1

class BoomSystem(BaseModel):
    pivot_offset_x_m: float
    pivot_offset_z_m: float
    base_section: BoomSection
    tip_section: BoomSection
    inserts: List[BoomInsert] = []

class CraneData(BaseModel):
    id: str
    model_name: str
    max_capacity_ton: float
    base_structure: BaseStructure
    crawler_system: CrawlerSystem
    counterweight_configs: List[CounterweightConfig]
    boom_system: BoomSystem

class CraneLibrary(BaseModel):
    cranes: List[CraneData]
