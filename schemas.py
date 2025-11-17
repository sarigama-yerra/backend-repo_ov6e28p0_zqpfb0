"""
Database Schemas for PC Building Simulator

Each Pydantic model corresponds to a MongoDB collection. The collection name is the lowercase of the class name.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict

ComponentType = Literal[
    "cpu",
    "motherboard",
    "ram",
    "gpu",
    "storage",
    "psu",
    "case"
]

class Component(BaseModel):
    """
    PC components catalog
    Collection name: "component"
    """
    type: ComponentType = Field(..., description="Component category")
    name: str = Field(..., description="Display name")
    brand: Optional[str] = Field(None, description="Manufacturer brand")
    price: float = Field(..., ge=0, description="Price in USD")

    # Compatibility fields (optional, used where relevant)
    socket: Optional[str] = Field(None, description="CPU/Motherboard socket type")
    chipset: Optional[str] = Field(None, description="Motherboard chipset")
    ram_type: Optional[str] = Field(None, description="Supported RAM type e.g., DDR4, DDR5")
    ram_speed: Optional[int] = Field(None, description="Max supported RAM speed in MHz")
    tdp: Optional[int] = Field(None, description="Thermal Design Power in Watts (CPU/GPU)")
    power_draw: Optional[int] = Field(None, description="Typical power draw in Watts")
    capacity_gb: Optional[int] = Field(None, description="Capacity in GB (RAM/Storage)")
    form_factor: Optional[str] = Field(None, description="Motherboard/Case form factor e.g., ATX, mATX, ITX")
    supported_form_factors: Optional[List[str]] = Field(None, description="Case supported motherboard sizes")

class Build(BaseModel):
    """
    Saved builds with selected parts
    Collection name: "build"
    """
    name: str = Field(..., description="Build name")
    cpu_id: Optional[str] = None
    motherboard_id: Optional[str] = None
    ram_id: Optional[str] = None
    gpu_id: Optional[str] = None
    storage_id: Optional[str] = None
    psu_id: Optional[str] = None
    case_id: Optional[str] = None

    total_price: Optional[float] = Field(0, description="Computed total price")
    total_power: Optional[int] = Field(0, description="Estimated total power draw")
    compatibility: Optional[Dict[str, str]] = Field(default_factory=dict, description="Compatibility check results")
