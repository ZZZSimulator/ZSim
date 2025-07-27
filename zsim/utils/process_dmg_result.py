import json
import os

import polars as pl
from zsim.define import ANOMALY_MAPPING
from zsim.sim_progress.Character.skill_class import lookup_name_or_cid

from .constants import results_dir, SKILL_TAG_MAPPING


def _load_dmg_data(rid: int | str) -> pl.DataFrame | None:
    """加载指定运行ID的伤害数据CSV文件。

    Args:
        rid (int): 运行ID。

    Returns:
        Optional[pd.DataFrame]: 加载的伤害数据DataFrame，如果文件未找到则返回None。
    """
    csv_file_path = os.path.join(results_dir, str(rid), "damage.csv")
    try:
        lf = pl.scan_csv(csv_file_path)
        # 去除列名中的特殊字符
        schema_names = lf.collect_schema().names()
        lf = lf.rename(
            {col: col.replace("\r", "").replace("\n", "").strip() for col in schema_names}
        )
        return lf.collect()
    except FileNotFoundError:
        print(f"未找到文件：{csv_file_path}")
        return None


def prepare_line_chart_data(dmg_result_df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """准备用于绘制伤害与失衡曲线图的数据。

    Args:
        dmg_result_df (pl.DataFrame): 原始伤害数据。

    Returns:
        dict[str, Any]: 包含处理后数据的字典，用于绘制折线图。
            - 'line_chart_df': 包含时间、伤害、DPS、失衡值、失衡效率的DataFrame。
    """
    processed_df = dmg_result_df.clone()

    # 计算DPS
    processed_df = processed_df.with_columns(
        (pl.col("dmg_expect").cum_sum() / pl.col("tick") * 60).alias("dps")
    )

    # 处理失衡值
    if "失衡状态" in processed_df.columns:
        processed_df = processed_df.with_columns(
            pl.when(pl.col("失衡状态")).then(0).otherwise(pl.col("stun")).alias("stun")
        )

    # 计算失衡效率
    first_stun_row = processed_df.filter(pl.col("失衡状态") == True).head(1)  # noqa: E712
    if len(first_stun_row) > 0:
        first_stun_tick = first_stun_row["tick"][0]
        before_stun = processed_df.filter(pl.col("tick") <= first_stun_tick)
        after_stun = processed_df.filter(pl.col("tick") > first_stun_tick)

        before_stun = before_stun.with_columns(
            (pl.col("stun").cum_sum() / pl.col("tick") * 60).alias("stun_efficiency")
        )
        after_stun = after_stun.with_columns(pl.lit(None).alias("stun_efficiency"))
        processed_df = pl.concat([before_stun, after_stun])
    else:
        processed_df = processed_df.with_columns(
            (pl.col("stun").cum_sum() / pl.col("tick") * 60).alias("stun_efficiency")
        )

    return {"line_chart_df": processed_df}


def _get_cn_skill_tag(skill_tag: str) -> str:
    """根据技能标签获取技能中文名。

    Args:
        skill_tag (str): 技能标签。

    Returns:
        str: 技能中文名。
    """
    return SKILL_TAG_MAPPING.get(skill_tag, skill_tag)


def sort_df_by_UUID(dmg_result_df: pl.DataFrame) -> pl.DataFrame:
    """按UUID对伤害数据进行分组和聚合。

    Args:
        dmg_result_df (pl.DataFrame): 原始伤害数据。

    Returns:
        pl.DataFrame: 按UUID聚合后的数据，包含每个UUID的总伤害、总失衡、总积蓄等信息。

    Raises:
        ValueError: 如果DataFrame缺少必要的列。
    """
    required_columns = [
        "skill_tag",
        "dmg_expect",
        "stun",
        "buildup",
        "UUID",
        "is_anomaly",
    ]
    for col in required_columns:
        if col not in dmg_result_df.columns or dmg_result_df[col].is_null().all():
            raise ValueError(f"DataFrame 中缺少有效的列: {col}")

    result_data = []
    all_UUID = dmg_result_df["UUID"].unique().to_list()

    for UUID in all_UUID:
        same_UUID_rows = dmg_result_df.filter(pl.col("UUID") == UUID)
        dmg_expect_sum = same_UUID_rows["dmg_expect"].fill_null(0).sum()
        stun_sum = same_UUID_rows["stun"].fill_null(0).sum()
        buildup_sum = same_UUID_rows["buildup"].fill_null(0).sum()

        skill_tags = same_UUID_rows["skill_tag"].drop_nulls()
        skill_tag = skill_tags[0] if len(skill_tags) > 0 else None
        is_anomaly = same_UUID_rows["is_anomaly"][0]
        element_types = same_UUID_rows["element_type"].drop_nulls()
        element_type = element_types[0] if len(element_types) > 0 else None

        cid: int | str | None = None
        name: str | None = None
        skill_cn_name: str | None = None
        if skill_tag:
            cid_str = skill_tag[0:4]
            skill_cn_name = _get_cn_skill_tag(skill_tag)  # 获取技能中文名
            try:
                name, cid_lookup = lookup_name_or_cid(cid=cid_str)
                cid = cid_lookup
            except ValueError:
                name = skill_tag  # 如果查找失败，使用skill_tag作为名字
                cid = None
        else:
            skill_cn_name = "Unknown"  # 如果没有skill_tag，则设为Unknown

        result_data.append(
            {
                "UUID": UUID,
                "name": name,
                "element_type": element_type,
                "is_anomaly": is_anomaly,
                "cid": cid,
                "skill_tag": skill_tag,
                "skill_cn_name": skill_cn_name,  # 添加技能中文名
                "dmg_expect_sum": dmg_expect_sum,
                "stun_sum": stun_sum,
                "buildup_sum": buildup_sum,
            }
        )

    return pl.DataFrame(result_data)


def prepare_char_chart_data(uuid_df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """准备用于绘制角色参与度分布图的数据。

    Args:
        uuid_df (pl.DataFrame): 按UUID聚合后的伤害数据。

    Returns:
        Dict[str, Any]: 包含绘制饼图所需数据的字典。
            - 'char_dmg_df': 按角色分组的伤害总和。
            - 'char_stun_df': 按角色分组的失衡总和。
            - 'char_skill_dmg_df': 按角色和技能标签分组的伤害总和。
            - 'char_element_df': 按角色和元素类型分组的积蓄总和。
    """
    # 各伤害来源占比
    char_dmg_df = (
        uuid_df.filter(pl.col("dmg_expect_sum") > 0)
        .group_by(["name", "is_anomaly"])
        .agg(pl.col("dmg_expect_sum").sum())
    )

    # 角色失衡占比
    char_stun_df = (
        uuid_df.filter(pl.col("stun_sum") > 0).group_by("name").agg(pl.col("stun_sum").sum())
    )

    # 角色技能输出占比
    filtered_skill_df = uuid_df.filter(pl.col("cid").is_not_null())
    char_skill_dmg_df = filtered_skill_df.group_by(["name", "skill_cn_name"]).agg(
        [
            pl.col("dmg_expect_sum").sum(),
            pl.col("buildup_sum").sum(),
            pl.col("stun_sum").sum(),
        ]
    )

    # 角色属性积蓄占比
    filtered_buildup_df = uuid_df.filter(pl.col("buildup_sum") > 0)
    char_element_df = filtered_buildup_df.group_by(["name", "element_type"]).agg(
        pl.col("buildup_sum").sum()
    )

    return {
        "char_dmg_df": char_dmg_df,
        "char_stun_df": char_stun_df,
        "char_skill_dmg_df": char_skill_dmg_df,
        "char_element_df": char_element_df,
    }


def _find_consecutive_true_ranges(df: pl.DataFrame, column: str) -> list[tuple[int, int]]:
    """查找DataFrame列中连续为True的范围。

    Args:
        df (pl.DataFrame): 输入的DataFrame，需要包含 'tick' 列。
        column (str): 要查找的布尔列名。

    Returns:
        list[tuple[int, int]]: 一个包含 (开始tick, 结束tick) 元组的列表。
    """
    ranges = []
    start = None

    # 获取tick列和指定列的值
    ticks = df["tick"].to_list()
    values = df[column].to_list()

    for i, (tick, value) in enumerate(zip(ticks, values)):
        if value:
            if start is None:
                start = tick
        else:
            if start is not None:
                # 结束tick应该是上一个为True的tick
                prev_tick = ticks[i - 1] if i > 0 else start
                ranges.append((start, prev_tick))
                start = None
    # 处理最后一个区间（如果存在）
    if start is not None:
        ranges.append((start, ticks[-1]))
    return ranges


def prepare_timeline_data(dmg_result_df: pl.DataFrame) -> pl.DataFrame | None:
    """准备用于绘制异常状态时间线的数据。

    Args:
        dmg_result_df (pl.DataFrame): 原始伤害数据。

    Returns:
        Optional[pl.DataFrame]: 用于绘制Gantt图的DataFrame，如果缺少列或无数据则返回None。
    """
    required_columns = [
        "冻结",
        "霜寒",
        "畏缩",
        "感电",
        "灼烧",
        "侵蚀",
        "烈霜霜寒",
        "tick",
    ]
    missing_cols = [col for col in required_columns if col not in dmg_result_df.columns]
    if missing_cols:
        print(f"输入数据缺少必要的列: {missing_cols}")
        return None

    columns_to_check = ["冻结", "霜寒", "畏缩", "感电", "灼烧", "侵蚀", "烈霜霜寒"]
    gantt_data = []
    for col in columns_to_check:
        if col in dmg_result_df.columns:
            ranges = _find_consecutive_true_ranges(dmg_result_df, col)
            for start, end in ranges:
                gantt_data.append({"Task": col, "Start": start, "Finish": end})

    if not gantt_data:
        return None

    gantt_df = pl.DataFrame(gantt_data)
    gantt_df = gantt_df.with_columns(
        (pl.col("Finish") - pl.col("Start") + 1).alias("Duration")
    )  # 持续时间包含首尾
    return gantt_df


def calculate_and_save_anomaly_attribution(
    rid: int, char_dmg_df: pl.DataFrame, char_element_df: pl.DataFrame
) -> None:
    """计算并保存异常伤害归因。

    Args:
        rid (int): 运行ID。
        char_dmg_df (pd.DataFrame): 角色直接伤害数据。
        char_element_df (pd.DataFrame): 角色元素积蓄数据。
    """
    output_path = f"{results_dir}/{rid}/damage_attribution.json"
    # 检查文件是否已存在
    if os.path.exists(output_path):
        return
    # 计算每种元素类型的异常总伤害
    anomaly_name_list = list(ANOMALY_MAPPING.values()) + ["极性紊乱", "异放"]
    anomaly_damage_totals = {element: 0 for element in anomaly_name_list}
    for anomaly_name in anomaly_name_list:
        if anomaly_name in char_dmg_df["name"].to_list():
            filtered_df = char_dmg_df.filter(pl.col("name") == anomaly_name)
            for row in filtered_df.iter_rows(named=True):
                anomaly_damage_totals[anomaly_name] += row["dmg_expect_sum"]

    # 初始化一个包含所有角色的字典
    all_characters = set(char_dmg_df.filter(~pl.col("is_anomaly"))["name"].to_list()).union(
        set(char_element_df["name"])
    )

    # 初始化角色伤害数据
    attribution_data: dict[str, dict[str, float]] = {
        name: {"direct_damage": 0, "anomaly_damage": 0} for name in all_characters
    }

    # 处理只打出直伤的角色
    for row in char_dmg_df.filter(~pl.col("is_anomaly")).iter_rows(named=True):
        name = row["name"]
        direct_damage = row["dmg_expect_sum"]
        attribution_data[name]["direct_damage"] = direct_damage

    # 分配异常伤害到角色
    for row in char_element_df.iter_rows(named=True):
        name = row["name"]
        element_type = row["element_type"]
        buildup_sum = row["buildup_sum"]
        anomaly_name = ANOMALY_MAPPING[element_type]
        total_anomaly_damage = anomaly_damage_totals[anomaly_name]

        # 计算角色的异常伤害归因
        if total_anomaly_damage > 0:
            element_total = char_element_df.filter(pl.col("element_type") == element_type)[
                "buildup_sum"
            ].sum()
            anomaly_damage_attribution = (buildup_sum / element_total) * total_anomaly_damage
        else:
            anomaly_damage_attribution = 0

        # 更新角色的异常伤害
        attribution_data[name]["anomaly_damage"] += anomaly_damage_attribution

    # 处理极性紊乱和异放
    for anomaly_name in ["极性紊乱", "异放"]:
        total_anomaly_damage = anomaly_damage_totals.get(anomaly_name, 0)
        if total_anomaly_damage > 0:
            if anomaly_name == "极性紊乱":
                for key in attribution_data:
                    if key == "柳":
                        attribution_data[key]["anomaly_damage"] += total_anomaly_damage
            if anomaly_name == "异放":
                for key in attribution_data:
                    if key == "薇薇安":
                        attribution_data[key]["anomaly_damage"] += total_anomaly_damage

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(attribution_data, f, ensure_ascii=False, indent=4)


def prepare_dmg_data_and_cache(
    rid: int | str,
) -> dict[str, pl.DataFrame | dict[str, pl.DataFrame]] | None:
    """准备并缓存伤害分析所需的数据。

    Args:
        rid (int): 运行ID。

    Returns:
        Optional[dict[str, pl.DataFrame]]: 包含预处理后的数据的字典，
        如果没有数据则返回None。
    """
    dmg_result_df = _load_dmg_data(rid)
    if dmg_result_df is None:
        return None
    uuid_df = sort_df_by_UUID(dmg_result_df)
    char_chart_data = prepare_char_chart_data(uuid_df)
    # st.write(char_chart_data)
    calculate_and_save_anomaly_attribution(
        int(rid), char_chart_data["char_dmg_df"], char_chart_data["char_element_df"]
    )
    return {
        "dmg_result_df": dmg_result_df,
        "char_dmg_df": char_chart_data["char_dmg_df"],
        "uuid_df": uuid_df,
        "char_chart_data": char_chart_data,
    }
