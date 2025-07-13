import importlib
from typing import TYPE_CHECKING, Type

from .character import Character
from .skill_class import lookup_name_or_cid

if TYPE_CHECKING:
    from zsim.models.session.session_run import CharConfig, ExecAttrCurveCfg, ExecWeaponCfg


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
    char_config: "CharConfig",
    *,
    sim_cfg: "ExecAttrCurveCfg | ExecWeaponCfg | None" = None,
) -> Character:
    """
    角色工厂函数，用于创建角色实例

    参数：
    - char_config: CharConfig对象，包含角色的所有配置信息
    - sim_cfg: 模拟配置对象，可选参数，用于特殊模拟模式

    返回：
    - Character: 角色实例
    """
    name, CID = lookup_name_or_cid(char_config.name, char_config.CID)

    if name in __char_module_map:
        try:
            module_name = __char_module_map[name]
            module = importlib.import_module(f".{module_name}", package=__name__)
            character_class: Type[Character] = getattr(module, module_name)
            return character_class(char_config=char_config, sim_cfg=sim_cfg)
        except ModuleNotFoundError:
            return Character(char_config=char_config, sim_cfg=sim_cfg)
    else:
        return Character(char_config=char_config, sim_cfg=sim_cfg)
