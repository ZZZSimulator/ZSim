from typing import TYPE_CHECKING

from .AdrenalineEventClass import AuricArray, AuricInkUndercurrent, BaseAdrenalineEvent

if TYPE_CHECKING:
    from zsim.sim_progress.Character.Yixuan import Yixuan
    from zsim.sim_progress.Preload import SkillNode
ADRENALINE_EVENT_LIST = [AuricArray, AuricInkUndercurrent]


def adrenaline_event_factory(char_instance: "Yixuan") -> list:
    event_list = []
    for event in ADRENALINE_EVENT_LIST:
        if event == AuricInkUndercurrent:
            if not char_instance.additional_abililty_active:
                continue
        event_list.append(event(char_instance=char_instance))

    return event_list


class AdrenalineManager:
    """仪玄有各种回复闪能的事件，所以统一写一个Manger来管理它们。"""

    def __init__(self, char_instance: "Yixuan"):
        self.char = char_instance
        self.adrenaline_recover_event_group: list[BaseAdrenalineEvent] | None = None

    def broadcast(self, skill_node: "SkillNode"):
        """向所有回能事件进行广播"""
        if self.adrenaline_recover_event_group is None:
            self.adrenaline_recover_event_group = adrenaline_event_factory(char_instance=self.char)
        for event in self.adrenaline_recover_event_group:
            event.update_status(skill_node=skill_node)

    def refresh(self):
        for event in self.adrenaline_recover_event_group:
            event.check_myself()
