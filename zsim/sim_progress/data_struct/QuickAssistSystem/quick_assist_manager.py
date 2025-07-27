from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Character import Character
    from zsim.sim_progress.Preload import SkillNode


class QuickAssistManager:
    """角色个人的快支管理器"""

    def __init__(self, char: "Character"):
        self.char = char
        self.start_tick = 0
        self.max_duration = 60  # 快速支援亮起的最大持续时间
        self.end_tick = 0
        self.quick_assist_available = False  # 快速支援是否亮起
        self.quick_assist_skill = f"{self.char.CID}_BH_Aid"  # 快速支援技能名
        self.assist_event_update_tick = 0  # 快速支援事件上报给eventlist的tick
        self.last_update_node: "SkillNode | None" = None  # 上一次导致快速支援激活的技能。

    def assist_waiting_for_anwser(self, tick: int) -> bool:
        """检查当前是否处于“快速支援即将触发但还未触发”的状态"""
        checked_node = self.last_update_node
        if checked_node is None:
            # 如果last_update_node是None，那说明当前根本没有技能尝试触发过快速支援，直接返回False
            return False

        if checked_node.preload_tick + checked_node.skill.aid_lag_ticks > tick:
            return True
        else:
            return False

    def state_change(self, tick: int, **kwargs) -> None:
        """改变自身状态。"""
        operation = kwargs.get("operation", None)
        answer = kwargs.get("answer", False)  # noqa: F841
        if operation == "turn_on":
            self.start_tick = tick
            self.quick_assist_available = True
            self.end_tick = tick + self.max_duration
            # print(f'{self.char.NAME}的快速支援亮起了！')
        elif operation == "turn_off":
            if not self.quick_assist_available:
                """这个分支意味着，快速支援早就因角色提前响应而被关闭，此时不需要更新，直接return"""
                return
            self.quick_assist_available = False
            self.end_tick = tick
            # if answer:
            #     print(f'{self.char.NAME}响应了快速支援，使其提前结束！')
            # else:
            #     print(f'{self.char.NAME}忽略了快速支援，使其到期结束！')
        else:
            raise ValueError("传入了快支管理器无法解析的参数！")
