from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


def find_char_from_CID(CID: int, sim_instance: "Simulator"):
    char_list = sim_instance.char_data.char_obj_list
    for char in char_list:
        if char.CID == CID:
            return char
    else:
        raise ValueError(f"并未找到CID为{CID}的角色！")
