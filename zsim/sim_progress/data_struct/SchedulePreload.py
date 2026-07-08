from typing import TYPE_CHECKING

from .schedule_dispatch import ScheduledEventEmitterProvider

if TYPE_CHECKING:
    from zsim.sim_progress.Preload.PreloadDataClass import PreloadData
    from zsim.simulator.simulator_class import Simulator


class SchedulePreload:
    def __init__(
        self,
        preload_tick: int,
        skill_tag: str,
        preload_data=None,
        apl_priority: int = 0,
        active_generation: bool = False,
        sim_instance: "Simulator | None" = None,
    ) -> None:
        """计划Preload事件，用于在指定的tick执行Preload的添加，通常用于协同攻击、附加伤害、延后追加攻击事件的创建。
        Args:
            preload_tick (int): 事件执行的tick
            skill_tag (str): 事件的标签，用于识别事件
            preload_data (PreloadData, optional): 事件的Preload数据，用于添加Preload。Defaults to None.
            apl_priority (int, optional): 事件的APL优先级，用于排序。Defaults to 0.
            active_generation (bool, optional): 事件是否为主动生成的，用于判断是否需要添加到事件列表中。Defaults to False.
            sim_instance (Simulator | None, optional): 事件所在的模拟器实例，用于获取当前的tick和事件列表。Defaults to None.
        """
        self.execute_tick: int = preload_tick
        self.skill_tag: str = skill_tag
        self.preload_data: "PreloadData | None" = preload_data
        self.apl_priority: int = apl_priority
        self.active_generation: bool = active_generation
        self.sim_instance = sim_instance

    def execute_myself(self):
        if self.preload_data is None:
            from zsim.sim_progress.Buff import JudgeTools

            self.preload_data = JudgeTools.find_preload_data(sim_instance=self.sim_instance)
        info_tuple = (self.skill_tag, self.active_generation, self.apl_priority)
        self.preload_data.external_add_skill(info_tuple)


def schedule_preload_event_factory(
    preload_tick_list: list[int],
    skill_tag_list: list[str],
    preload_data,
    sim_instance: "Simulator",
    apl_priority_list: list[int] | None = None,
    active_generation_list: list[bool] | None = None,
    scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
) -> None:
    """根据传入的参数，生成SchedulePreload事件；通常情况下我们不通过构造函数直接创建SchedulePreload事件，而是通过调用此工厂函数来创建事件。
    Args:
        preload_tick_list (list[int]): 事件执行的tick列表
        skill_tag_list (list[str]): 事件的标签列表，用于识别事件
        preload_data (_type_): 事件的Preload数据，用于添加Preload
        sim_instance (Simulator): 事件所在的模拟器实例，用于获取当前的tick和事件列表
        apl_priority_list (list[int] | None, optional): 事件的APL优先级列表，用于排序。Defaults to None.
        active_generation_list (list[bool] | None, optional): 事件是否为主动生成的列表，用于判断是否需要添加到事件列表中。Defaults to None.
    """
    event_count = len(skill_tag_list)
    from zsim.sim_progress.Buff import JudgeTools

    tick_now = JudgeTools.find_tick(sim_instance=sim_instance)
    if len(preload_tick_list) != event_count:
        raise ValueError("preload_tick_list和skill_tag_list的长度不一致")
    if apl_priority_list is not None and len(apl_priority_list) != event_count:
        raise ValueError("apl_priority_list和skill_tag_list的长度不一致")
    if active_generation_list is not None and len(active_generation_list) != event_count:
        raise ValueError("active_generation_list和skill_tag_list的长度不一致")
    emitter_provider = (
        scheduled_event_emitter_provider
        or ScheduledEventEmitterProvider.from_sim_instance(sim_instance)
    )
    emitter = emitter_provider.create_emitter()
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
            preload_tick,
            skill_tag,
            preload_data,
            apl_priority,
            active_generation,
            sim_instance=sim_instance,
        )
        emitter.emit_scheduled(schedule_event)
