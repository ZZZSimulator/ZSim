from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


def find_char_from_name(NAME: str, sim_instance: "Simulator" = None):
    char_list = sim_instance.char_data.char_obj_list
    for _ in char_list:
        if _.NAME == NAME:
            return _
    else:
        raise ValueError(f"未找到名为{NAME}的角色")
