import polars as pl
import streamlit as st
from zsim.define import ElementType


@st.cache_data
def _init_buff_effect_mapping() -> dict[str, str]:
    """初始化BUFF效果映射关系"""
    try:
        df = pl.scan_csv("./zsim/data/buff_effect.csv")
        mapping = df.collect().to_dict(as_series=False)
        buff_effect_map: dict[str, str] = {}
        for i in range(len(mapping["名称"])):
            name = mapping["名称"][i]
            effect_str = ""
            # 动态的找键值对数量
            max_key_index = 0
            for col_name in mapping.keys():
                if col_name.startswith("key"):
                    try:
                        index = int(col_name[3:])
                        if index > max_key_index:
                            max_key_index = index
                    except ValueError:
                        # 忽略不符合 keyN 格式的列名
                        pass

            for j in range(1, max_key_index + 1):
                key_col = f"key{j}"
                value_col = f"value{j}"
                if key_col in mapping and value_col in mapping:
                    key = mapping[key_col][i]
                    value = mapping[value_col][i]
                    if key and value is not None:
                        try:
                            effect_str += f"{key}: {float(value)}; "
                        except ValueError:
                            # Handle cases where value is not a valid float
                            print(
                                f"Warning: Could not convert value '{value}' to float for buff '{name}', key '{key}'. Skipping this effect."
                            )
                            continue
            if effect_str:
                # Remove trailing semicolon and space if present
                buff_effect_map[name] = effect_str.rstrip("; ")
        return buff_effect_map
    except Exception as e:
        print(f"Warning: Failed to load buff effect mapping: {e}")
        return {}


BUFF_EFFECT_MAPPING: dict[str, str] = _init_buff_effect_mapping()


@st.cache_data
def _init_skill_tag_mapping() -> dict[str, str]:
    """初始化技能标签映射关系"""
    try:
        df = pl.scan_csv(
            "./zsim/data/skill.csv",
            schema_overrides={
                "skill_tag": pl.String,
                "skill_text": pl.String,
                "INSTRUCTION": pl.String,
            },
        )
        mapping = (
            df.select("skill_tag", "skill_text", "INSTRUCTION").collect().to_dict(as_series=False)
        )
        return {
            _tag: f"{_text if _text else ''}{f' - {_instruction}' if _instruction else ''}"
            for _tag, _text, _instruction in zip(
                mapping["skill_tag"], mapping["skill_text"], mapping["INSTRUCTION"]
            )
        }
    except Exception as e:
        print(f"Warning: Failed to load skill mapping: {e}")
        return {}


SKILL_TAG_MAPPING: dict[str, str] = _init_skill_tag_mapping()


@st.cache_data
def _init_char_mapping() -> dict[str, str]:
    """初始化角色CID和名称的映射关系"""
    try:
        df = pl.scan_csv("./zsim/data/character.csv")
        mapping = df.select(["name", "CID"]).collect().to_dict(as_series=False)
        return {name: str(cid) for name, cid in zip(mapping["name"], mapping["CID"])}
    except Exception as e:
        print(f"Warning: Failed to load character mapping: {e}")
        return {}


# 角色CID和名称的映射关系
CHAR_CID_MAPPING: dict[str, str] = _init_char_mapping()

# 角色配置常量
default_chars = [
    "扳机",
    "丽娜",
    "零号·安比",
]  # 这个值其实没啥意义，但是必须是三个角色，否则可能会报错
__lf_character = pl.scan_csv("./zsim/data/character.csv")
char_options = __lf_character.select("name").unique().collect().to_series().to_list()
# 角色名称->职业特性
char_profession_map = {row["name"]: row["角色特性"] for row in __lf.collect().iter_rows(named=True)}

# 职业特性->角色名称列表
profession_chars_map = {}
for char_name, profession in char_profession_map.items():
    if profession not in profession_chars_map:
        profession_chars_map[profession] = []
    profession_chars_map[profession].append(char_name)

profession_chars_map["不限特性"] = char_options

# 武器选项
__lf_weapon = pl.scan_csv("./zsim/data/weapon.csv")
weapon_options = __lf_weapon.select("名称").unique().collect().to_series().to_list()
# 音擎名称->职业
weapon_profession_map = {row["名称"]: row["职业"] for row in __lf.collect().iter_rows(named=True)}
# 音擎名称->稀有度
weapon_rarity_map = {
    row["名称"]: row["稀有度"] for row in __lf_weapon.collect().iter_rows(named=True)
}
# 音擎名称->角色名称 (仅限部分 S 级和 A 级)
weapon_char_map: dict[str, str] = {}
for row in __lf_weapon.collect().iter_rows(named=True):
    cid = row["ID"] % 1000 * 10 + 1
    names = (
        __lf_character
        .filter(pl.col("CID") == cid)
        .select("name")
        .collect()
        .to_series()
        .to_list()
    )
    # 如果没有对应角色，默认用空字符串
    weapon_char_map[row["名称"]] = names[0] if names else ""

# 驱动盘套装选项
__lf_equip = pl.scan_csv("./zsim/data/equip_set_2pc.csv")
equip_set_ids = (
    __lf_equip.select("set_ID")
    .filter(pl.col("set_ID").is_not_null())
    .unique()
    .collect()
    .to_series()
    .to_list()
)
equip_set4_options = equip_set2_options = equip_set_ids

# 主词条选项
main_stat4_options = [
    "攻击力%",
    "生命值%",
    "防御力%",
    "暴击率%",
    "暴击伤害%",
    "异常精通",
    "-",
]
main_stat5_options = [
    "攻击力%",
    "生命值%",
    "防御力%",
    "穿透率",
    "物理属性伤害%",
    "火属性伤害%",
    "冰属性伤害%",
    "电属性伤害%",
    "以太属性伤害%",
    "-",
]
main_stat6_options = [
    "攻击力%",
    "生命值%",
    "防御力%",
    "异常掌控",
    "冲击力%",
    "能量自动回复%",
    "-",
]

stats_trans_mapping = {
    "攻击力%": "scATK_percent",
    "攻击力": "scATK",
    "生命值%": "scHP_percent",
    "生命值": "scHP",
    "防御力%": "scDEF_percent",
    "防御力": "scDEF",
    "异常精通": "scAnomalyProficiency",
    "穿透值": "scPEN",
    "暴击率": "scCRIT",
    "暴击伤害": "scCRIT_DMG",
    "属性伤害加成": "DMG_BONUS",
    "穿透率": "PEN_RATIO",
    "异常掌控": "ANOMALY_MASTERY",
    "能量自动回复": "SP_REGEN",
}

SC_DATA_DISCRIPTION_MAPPING = {
    "scATK_percent": "3%/词条",
    "scATK": "19点/词条",
    "scHP_percent": "3%/词条",
    "scHP": "112/词条",
    "scDEF_percent": "4.8%/词条",
    "scDEF": "15点/词条",
    "scAnomalyProficiency": "9点/词条",
    "scPEN": "9点/词条",
    "scCRIT": "2.4%暴击率或4.8%暴击伤害/词条",
    "scCRIT_DMG": "2.4%暴击率或4.8%暴击伤害/词条",
    "DMG_BONUS": "3%/词条",
    "PEN_RATIO": "2.4%/词条",
    "ANOMALY_MASTERY": "3%/词条",
    "SP_REGEN": "6%/词条",
}

# 副词条最大值
sc_max_value = 40

# 计算结果缓存文件路径
ID_CACHE_JSON = "./results/id_cache.json"
results_dir = "./results"

# 六元素翻译对应表
element_mapping: dict[ElementType, str] = {
    0: "物理",
    1: "火",
    2: "冰",
    3: "电",
    4: "以太",
    5: "烈霜",
    6: "玄墨",
}


# ID重复时抛出的自定义异常类
class IDDuplicateError(Exception):
    """当检测到重复ID时抛出此异常"""

    pass

# 确保在文件末尾删除临时变量
del __lf_character 
del __lf_weapon
del __lf_equip
