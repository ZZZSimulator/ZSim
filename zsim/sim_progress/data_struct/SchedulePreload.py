from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class SchedulePreload:
    def __init__(
        self,
        preload_tick: int,
        skill_tag: str,
        preload_data=None,
        apl_priority: int = 0,
        active_generation: bool = False,
        sim_instance: "Simulator" = None,
    ) -> None:
        """计划Preload事件"""
        self.execute_tick = preload_tick
        self.skill_tag = skill_tag
        self.preload_data = preload_data
        self.apl_priority = apl_priority
        self.active_generation = active_generation
        self.sim_instance = sim_instance

    def execute_myself(self):
        if self.preload_data is None:
            from zsim.sim_progress.Buff import JudgeTools

            self.preload_data = JudgeTools.find_preload_data(
                sim_instance=self.sim_instance
            )
        info_tuple = (self.skill_tag, self.active_generation, self.apl_priority)
        self.preload_data.external_add_skill(info_tuple)


def schedule_preload_event_factory(
    preload_tick_list: list[int],
    skill_tag_list: list[str],
    preload_data,
    apl_priority_list: list[int] = None,
    active_generation_list: list[bool] = None,
    sim_instance: "Simulator" = None,
) -> None:
    """根据传入的参数，生成SchedulePreload事件"""
    event_count = len(skill_tag_list)
    from zsim.sim_progress.Buff import JudgeTools

    tick_now = JudgeTools.find_tick(sim_instance=sim_instance)
    event_list = JudgeTools.find_event_list(sim_instance=sim_instance)
    if len(preload_tick_list) != event_count:
        raise ValueError("preload_tick_list和skill_tag_list的长度不一致")
    if apl_priority_list is not None and len(apl_priority_list) != event_count:
        raise ValueError("apl_priority_list和skill_tag_list的长度不一致")
    if (
        active_generation_list is not None
        and len(active_generation_list) != event_count
    ):
        raise ValueError("active_generation_list和skill_tag_list的长度不一致")
    for i in range(event_count):
        preload_tick = preload_tick_list[i]
        if preload_tick < tick_now:
            raise ValueError("不能添加过去的Preload计划事件")
        skill_tag = skill_tag_list[i]
        apl_priority = apl_priority_list[i] if apl_priority_list is not None else 0
        active_generation = (
            active_generation_list[i] if active_generation_list is not None else False
        )
        schedule_event = SchedulePreload(
            preload_tick, skill_tag, preload_data, apl_priority, active_generation
        )
        event_list.append(schedule_event)
