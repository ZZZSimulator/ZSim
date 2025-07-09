import importlib
from typing import Type

from .character import Character
from .skill_class import lookup_name_or_cid

__char_module_map = {
    "苍角": "Soukaku",
    "莱特": "Lighter",
    "艾莲": "Ellen",
    "雅": "Miyabi",
    "11号": "Soldier11",
    "青衣": "Qingyi",
    "朱鸢": "Zhuyuan",
    "伊芙琳": "Evelyn",
    "零号·安比": "Soldier0_Anby",
    "扳机": "Trigger",
    "柳": "Yanagi",
    "简": "Jane",
    "薇薇安": "Vivian",
    "耀嘉音": "AstraYao",
    "雨果": "Hugo",
    "仪玄": "Yixuan",
}


def character_factory(
    name: str = "",
    CID: int | None = None,  # 角色名字和CID-必填至少一个
    weapon=None,
    weapon_level=1,  # 武器名字-选填项
    equip_style: str = "4+2",
    equip_set4=None,
    equip_set2_a=None,
    equip_set2_b=None,
    equip_set2_c=None,  # 驱动盘套装-选填项
    drive4=None,
    drive5=None,
    drive6=None,  # 驱动盘主词条-选填项
    scATK_percent=0,
    scATK=0,
    scHP_percent=0,
    scHP=0,
    scDEF_percent=0,
    scDEF=0,
    scAnomalyProficiency=0,
    scPEN=0,
    scCRIT=0,
    scCRIT_DMG=0,  # 副词条数量-选填项
    sp_limit=120,  # 能量上限-默认120
    cinema=0,
    crit_balancing=True,  # 暴击配平开关，默认开
    crit_rate_limit=0.95,  # 暴击率上限，默认0.95
    *,
    sim_cfg=None,
) -> Character:
    name, CID = lookup_name_or_cid(name, CID)
    char_init_args = {
        "name": name,
        "CID": CID,
        "weapon": weapon,
        "weapon_level": weapon_level,
        "equip_style": equip_style,
        "equip_set4": equip_set4,
        "equip_set2_a": equip_set2_a,
        "equip_set2_b": equip_set2_b,
        "equip_set2_c": equip_set2_c,
        "drive4": drive4,
        "drive5": drive5,
        "drive6": drive6,
        "scATK_percent": scATK_percent,
        "scATK": scATK,
        "scHP_percent": scHP_percent,
        "scHP": scHP,
        "scDEF_percent": scDEF_percent,
        "scDEF": scDEF,
        "scAnomalyProficiency": scAnomalyProficiency,
        "scPEN": scPEN,
        "scCRIT": scCRIT,
        "scCRIT_DMG": scCRIT_DMG,
        "sp_limit": sp_limit,
        "cinema": cinema,
        "crit_balancing": crit_balancing,
        "crit_rate_limit": crit_rate_limit,
        "sim_cfg": sim_cfg,
    }
    if name in __char_module_map:
        try:
            module_name = __char_module_map[name]
            module = importlib.import_module(f".{module_name}", package=__name__)
            character_class: Type[Character] = getattr(module, module_name)
            return character_class(**char_init_args)
        except ModuleNotFoundError:
            return Character(**char_init_args)
    else:
        return Character(**char_init_args)
