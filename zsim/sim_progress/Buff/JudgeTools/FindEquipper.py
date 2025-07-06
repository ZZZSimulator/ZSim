from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


def find_equipper(item_name: str, sim_instance: "Simulator" = None):
    """
    该函数用来找佩戴装备的人，但是需要注意，这个函数处理不了多个人同时佩戴同一件装备的情况。
    """
    Judge_list_set = sim_instance.init_data.Judge_list_set
    if "二件套" not in item_name:
        """默认找的是四件套 和武器"""
        for sub_list in Judge_list_set:
            for i in sub_list:
                if i == item_name and i != sub_list[3]:
                    return sub_list[0]
    else:
        """找的是二件套"""
        for sub_list in Judge_list_set:
            for i in sub_list:
                if i == item_name and i == sub_list[3]:
                    return sub_list[0]
