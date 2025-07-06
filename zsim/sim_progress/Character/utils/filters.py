from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import NewAnomaly
    from zsim.sim_progress.data_struct import SPUpdateData
    from zsim.sim_progress.Preload import SkillNode
    from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData


def _skill_node_filter(*args, **kwargs) -> list["SkillNode"]:
    """过滤出输入的 SKillNode，并作为列表返回"""
    from zsim.sim_progress.Preload import SkillNode

    skill_nodes: list[SkillNode] = []
    for arg in args:
        if isinstance(arg, SkillNode):
            skill_nodes.append(arg)
    for value in kwargs.values():
        if isinstance(value, SkillNode):
            skill_nodes.append(value)
    return skill_nodes


def _multiplier_filter(*args, **kwargs) -> list["MultiplierData"]:
    """过滤出输入的 乘区数据，并作为列表返回"""
    from zsim.sim_progress.ScheduledEvent.Calculator import MultiplierData

    multiplier_data: list[MultiplierData] = []
    for arg in args:
        if isinstance(arg, MultiplierData):
            multiplier_data.append(arg)
    for value in kwargs.values():
        if isinstance(value, MultiplierData):
            multiplier_data.append(value)
    return multiplier_data


def _sp_update_data_filter(*args, **kwargs) -> list["SPUpdateData"]:
    """过滤出输入的 SPUpdateData，并作为列表返回"""
    from zsim.sim_progress.data_struct import SPUpdateData

    sp_update_data: list[SPUpdateData] = []
    for arg in args:
        if isinstance(arg, SPUpdateData):
            sp_update_data.append(arg)
    for value in kwargs.values():
        if isinstance(value, SPUpdateData):
            sp_update_data.append(value)
    return sp_update_data


def _anomaly_filter(*args, **kwargs) -> list["NewAnomaly"]:
    """过滤出输入的异常类！并作为列表返回"""
    from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import NewAnomaly

    anomaly_bar_list: list[NewAnomaly] = []
    for arg in args:
        if isinstance(arg, NewAnomaly):
            anomaly_bar_list.append(arg)
    for value in kwargs.values():
        if isinstance(value, NewAnomaly):
            anomaly_bar_list.append(value)
    return anomaly_bar_list
