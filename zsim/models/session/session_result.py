import math
from collections.abc import Mapping
from typing import Any, Literal, Self, Union

import polars as pl
from pydantic import BaseModel, ConfigDict, Field, RootModel

# --- 不同结果类型的载荷 ---

NORMAL_RESULT_OPTIONAL_SECTIONS = ("dmg_result", "buff_result")
DAMAGE_RESULT_SECTIONS = (
    "dmg_result_df",
    "char_dmg_df",
    "uuid_df",
    "char_chart_data",
)
DAMAGE_UUID_AGGREGATE_FIELDS = (
    "UUID",
    "name",
    "element_type",
    "is_anomaly",
    "cid",
    "skill_tag",
    "skill_cn_name",
    "dmg_expect_sum",
    "stun_sum",
    "buildup_sum",
)
BUFF_TIMELINE_PUBLIC_FIELDS = ("Task", "Start", "Finish", "Value")
LEGACY_INTEGER_BUFF_TIMELINE_VALUE_TASKS = frozenset(
    {
        "Buff-角色-扳机-额外能力-追加攻击失衡值提升",
        "Buff-角色-雅-核心被动-冰焰",
        "Buff-角色-柚叶-组队被动-属性异常与紊乱伤害增幅",
        "Buff-角色-柚叶-组队被动-积蓄值增幅",
    }
)


def normalize_damage_result_schema(dmg_result_df: pl.DataFrame) -> pl.DataFrame:
    """统一工具、WebUI 与一致性代码使用的 damage.csv 结构变体。"""
    normalized = _normalize_bool_result_column(dmg_result_df, "is_anomaly")
    normalized = _normalize_bool_result_column(normalized, "is_disorder")
    if "skill_tag" not in normalized.columns:
        return normalized
    return normalized.with_columns(
        (
            pl.col("is_disorder")
            | pl.col("skill_tag").cast(pl.Utf8).str.contains("紊乱").fill_null(False)
        ).alias("is_disorder")
    )


def _normalize_bool_result_column(
    dmg_result_df: pl.DataFrame,
    column: str,
) -> pl.DataFrame:
    if column not in dmg_result_df.columns or dmg_result_df[column].is_null().all():
        return dmg_result_df.with_columns(pl.lit(False).alias(column))

    if dmg_result_df[column].dtype == pl.Boolean:
        return dmg_result_df.with_columns(pl.col(column).fill_null(False))

    return dmg_result_df.with_columns(
        pl.col(column)
        .cast(pl.Utf8)
        .str.to_lowercase()
        .is_in(["true", "1"])
        .fill_null(False)
        .alias(column)
    )


def normalize_result_contract_scalar(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            value = value.item()
        except (AttributeError, ValueError):
            pass
    if value is None:
        return None
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return round(float(value), 6)
    if isinstance(value, str):
        return value
    return str(value)


def normalize_buff_timeline_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        return normalize_result_contract_scalar(float(value))
    except (TypeError, ValueError):
        return normalize_result_contract_scalar(value)


def normalize_buff_timeline_display_value(task: Any, value: Any) -> Any:
    normalized = normalize_buff_timeline_value(value)
    if str(task) in LEGACY_INTEGER_BUFF_TIMELINE_VALUE_TASKS and isinstance(
        normalized, (int, float)
    ):
        return float(math.floor(float(normalized)))
    return normalized


def build_buff_timeline_entry(
    *,
    task: Any,
    start: Any,
    finish: Any,
    value: Any,
) -> dict[str, Any]:
    return {
        "Task": str(task),
        "Start": int(start),
        "Finish": int(finish),
        "Value": normalize_buff_timeline_display_value(task, value),
    }


def normalize_buff_timeline_entry(source: str, entry: Any) -> dict[str, Any]:
    if not isinstance(entry, Mapping):
        raise ValueError(f"'{source}' 的 Buff 时间线条目必须是对象")

    missing_fields = [field for field in BUFF_TIMELINE_PUBLIC_FIELDS if field not in entry]
    if missing_fields:
        raise ValueError(
            f"'{source}' 的 Buff 时间线条目缺少公开字段："
            + ", ".join(missing_fields)
        )

    return build_buff_timeline_entry(
        task=entry["Task"],
        start=entry["Start"],
        finish=entry["Finish"],
        value=normalize_buff_timeline_value(entry["Value"]),
    )


def normalize_buff_timeline_payload(payload: Any) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(payload, Mapping):
        raise ValueError("Buff 时间线载荷必须是按来源索引的对象")

    normalized: dict[str, list[dict[str, Any]]] = {}
    for source in sorted(payload, key=lambda item: str(item)):
        source_key = str(source)
        entries = payload[source]
        if entries is None:
            entries = []
        if not isinstance(entries, list):
            raise ValueError(f"'{source_key}' 的 Buff 时间线条目必须是列表")
        normalized[source_key] = [
            normalize_buff_timeline_entry(source_key, entry) for entry in entries
        ]
    return normalized


# --- 普通模式 ---
class DmgResult(RootModel[dict[str, Any] | None]):
    """
    伤害计算结果。

    根对象是一个字典，包含详细伤害分析所需的多组数据表（以字典列表表示）。
    为兼容 WebUI 处理函数，这里保留原有结构。
    """

    pass


class BuffTimelineBarValue(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    task: str = Field(description="Buff 名称", alias="Task")
    start: int = Field(description="Buff 开始 tick", alias="Start")
    finish: int = Field(description="Buff 结束 tick", alias="Finish")
    value: float = Field(description="Buff 数值或层数", alias="Value")


class BuffResult(RootModel[dict[str, list[BuffTimelineBarValue]] | None]):
    """
    Buff 时间线结果。

    根对象是一个字典，键为来源标识（例如文件键），值为 Buff 时间线点列表。
    """

    pass


class NormalResultPayload(BaseModel):
    dmg_result: DmgResult | None
    buff_result: BuffResult | None


# --- 并行模式 ---
class AttrCurvePoint(BaseModel):
    result: float = Field(description="该数据点的总伤害")
    rate: float | None = Field(description="相比上一个数据点的收益率")


class AttrCurvePayload(RootModel[dict[str, dict[str, dict[str, AttrCurvePoint]]]]):
    """
    属性曲线结果。

    结构：{char_name: {sc_name: {sc_value: point_data}}}
    """

    pass


class WeaponResultPoint(BaseModel):
    damage: float = Field(description="该武器配置下的总伤害")


class WeaponPayload(RootModel[dict[str, dict[str, dict[str, WeaponResultPoint]]]]):
    """
    武器对比结果。

    结构：{char_name: {weapon_name: {weapon_level: point_data}}}
    """

    pass


class ParallelAttrCurveResultPayload(BaseModel):
    func: Literal["attr_curve"]
    result: AttrCurvePayload


class ParallelWeaponResultPayload(BaseModel):
    func: Literal["weapon"]
    result: WeaponPayload


class ParallelResultPayload(
    RootModel[Union[ParallelAttrCurveResultPayload, ParallelWeaponResultPayload]]
):
    root: Union[ParallelAttrCurveResultPayload, ParallelWeaponResultPayload] = Field(
        ..., discriminator="func"
    )


# --- 带判别字段的联合模型 ---


class NormalModeResult(BaseModel):
    mode: Literal["normal"]
    result: NormalResultPayload


class ParallelModeResult(BaseModel):
    mode: Literal["parallel"]
    func: Literal["attr_curve", "weapon"]
    result: ParallelResultPayload


# --- 顶层 SessionResult 工厂类 ---


class SessionResult:
    """
    根据 `mode` 字段创建具体结果模型（NormalModeResult 或 ParallelModeResult）的工厂类。

    调用方可以按 `SessionResult(mode='normal', result=...)` 的形式实例化；
    返回值会是已经校验过的正确模型实例。它本身不是 Pydantic 模型，而是一个分发器。
    """

    def __new__(cls, **kwargs: Any) -> Self | NormalModeResult | ParallelModeResult:
        # 这里不是标准 Pydantic 模型，而是返回具体模型的工厂；接口形状要匹配控制器中的实例化方式。
        if cls is not SessionResult:
            # 允许子类在需要时按常规方式实例化。
            return super().__new__(cls)

        mode = kwargs.get("mode")
        if mode == "normal":
            return NormalModeResult(**kwargs)
        elif mode == "parallel":
            return ParallelModeResult(**kwargs)
        else:
            raise ValueError(f"SessionResult 收到无效 mode：{mode}")
