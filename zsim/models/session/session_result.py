from typing import Any, Literal, Self, Union

from pydantic import BaseModel, Field, RootModel


# --- Payloads for different result types ---

# --- Normal Mode ---
class DmgResult(RootModel[dict[str, Any] | None]):
    """
    Represents the damage calculation results.  
    The root is a dictionary containing various dataframes (as list of dicts)
    for detailed damage analysis. The structure is preserved from the webui
    processing functions for compatibility.
    """
    pass


class BuffTimelineBarValue(BaseModel):
    task: str = Field(description="Buff name", alias="Task")
    start: int = Field(description="Start tick of the buff", alias="Start")
    finish: int = Field(description="End tick of the buff", alias="Finish")
    value: float = Field(description="Buff value/stack", alias="Value")


class BuffResult(RootModel[dict[str, list[BuffTimelineBarValue]] | None]):
    """
    Represents the buff timeline results.
    The root is a dictionary where keys are source identifiers (e.g., file keys)
    and values are lists of buff timeline points.
    """
    pass


class NormalResultPayload(BaseModel):
    dmg_result: DmgResult | None
    buff_result: BuffResult | None


# --- Parallel Mode ---
class AttrCurvePoint(BaseModel):
    result: float = Field(description="Total damage for this data point")
    rate: float | None = Field(description="Rate of return compared to the previous point")


class AttrCurvePayload(RootModel[dict[str, dict[str, dict[str, AttrCurvePoint]]]]):
    """
    Represents the attribute curve results.
    Structure: {char_name: {sc_name: {sc_value: point_data}}}
    """
    pass


class WeaponResultPoint(BaseModel):
    damage: float = Field(description="Total damage for this weapon configuration")


class WeaponPayload(RootModel[dict[str, dict[str, dict[str, WeaponResultPoint]]]]):
    """
    Represents the weapon comparison results.
    Structure: {char_name: {weapon_name: {weapon_level: point_data}}}
    """
    pass


class ParallelAttrCurveResultPayload(BaseModel):
    func: Literal["attr_curve"]
    result: AttrCurvePayload


class ParallelWeaponResultPayload(BaseModel):
    func: Literal["weapon"]
    result: WeaponPayload


class ParallelResultPayload(RootModel[Union[ParallelAttrCurveResultPayload, ParallelWeaponResultPayload]]):
    root: Union[ParallelAttrCurveResultPayload, ParallelWeaponResultPayload] = Field(..., discriminator="func")


# --- Discriminated Union Models ---

class NormalModeResult(BaseModel):
    mode: Literal["normal"]
    result: NormalResultPayload


class ParallelModeResult(BaseModel):
    mode: Literal["parallel"]
    func: Literal["attr_curve", "weapon"]
    result: ParallelResultPayload


# --- Top-level SessionResult Factory Class ---

class SessionResult:
    """
    This class acts as a factory for creating specific result models
    (NormalModeResult or ParallelModeResult) based on the 'mode' field.
    It allows instantiation like `SessionResult(mode='normal', result=...)`,
    and the returned object will be a validated instance of the correct model.
    This is not a Pydantic model itself, but a dispatcher.
    """
    def __new__(cls, **kwargs: Any) -> Self | NormalModeResult | ParallelModeResult:
        # This is not a standard Pydantic model, but a factory that returns one.
        # It's designed to match the instantiation pattern in the controller.
        if cls is not SessionResult:
            # This allows subclasses to be instantiated normally if needed.
            return super().__new__(cls)

        mode = kwargs.get("mode")
        if mode == "normal":
            return NormalModeResult(**kwargs)
        elif mode == "parallel":
            return ParallelModeResult(**kwargs)
        else:
            raise ValueError(f"Invalid 'mode' for SessionResult: {mode}")