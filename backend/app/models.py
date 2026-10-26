"""Request/response models with range validation."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class LayerIn(BaseModel):
    t: Optional[float] = Field(default=None, ge=-10, le=70)
    rh: Optional[float] = Field(default=None, ge=0, le=100)


class LayersIn(BaseModel):
    top: LayerIn = LayerIn()
    mid: LayerIn = LayerIn()
    bot: LayerIn = LayerIn()
    amb: LayerIn = LayerIn()


class GasIn(BaseModel):
    mq135_mv: Optional[float] = Field(default=None, ge=0, le=5500)
    mq136_mv: Optional[float] = Field(default=None, ge=0, le=5500)
    mq135_base_mv: Optional[float] = Field(default=None, ge=0, le=5500)
    mq136_base_mv: Optional[float] = Field(default=None, ge=0, le=5500)


class ReadingIn(BaseModel):
    device_id: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    fw: Optional[str] = None
    uptime_s: int = Field(default=0, ge=0)
    age_s: int = Field(default=0, ge=0, le=7 * 24 * 3600)
    layers: LayersIn = LayersIn()
    gas: GasIn = GasIn()
    gas_alert: bool = False
    fan_on: bool = False
    fan_mode: str = "A"
    dropped: int = 0
    rssi: int = 0


class FanCommand(BaseModel):
    mode: Literal["on", "off", "auto"]
    ttl_s: int = Field(default=600, ge=30, le=24 * 3600)


class DeviceMeta(BaseModel):
    device_id: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    farmer: Optional[str] = Field(default=None, max_length=60)
    village: Optional[str] = Field(default=None, max_length=60)
    taluka: Optional[str] = Field(default=None, max_length=60)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lon: Optional[float] = Field(default=None, ge=-180, le=180)
    tonnes: Optional[float] = Field(default=None, ge=0, le=10000)
    crop: Optional[str] = Field(default="onion", max_length=20)


class SimControl(BaseModel):
    scenario: Optional[Literal["fresh", "humid", "rot"]] = None
    offline: Optional[bool] = None
    kit_on: Optional[bool] = None
    reset: Optional[bool] = None
