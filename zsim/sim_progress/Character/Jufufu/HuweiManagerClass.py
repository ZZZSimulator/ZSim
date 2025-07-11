from zsim.sim_progress.Preload import SkillNode
from zsim.define import JUFUFU_REPORT

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from zsim.sim_progress.Character.character import Character
    from zsim.simulator.simulator_class import Simulator


class HuweiManager:
    """虎威管理器，这里有虎威所有的数据机制以及业务逻辑"""
    def __init__(self, char_instance):
        self.char: "Character" = char_instance
        self.sim_instance: "Simulator | None" = None
        self.cd = 240       # 虎威的内置CD
        self.last_active_tick: int = 0  # 虎威上次激活的时间
        # FIXME: 在精细测帧之前，虎威的内置CD写成240tick
        self.occupied_state_update_tick: int = 0    # 占用事件的更新事件
        self.occupied_origin: SkillNode | None = None       # 虎威的占用源
        self.spinning_state: bool = False       # 高速旋转状态
        self.normal_attack_tag: str = "1391_SNA"     # 普攻攻击的技能tag
        self.ex_qte_tag: str = "1391_QTE_B"        # 强化连携技的技能tag
        self.ca_tag: str = "1391_CA_3"        # 强化旋转状态的技能tag
        self.occupied_skill_list: list[str] = ["1391_E_EX", "1391_CA_2", "1391_CA_3", "1391_QTE_A", "1391_QTE_B", "1391_Q"]

    @property
    def ready(self) -> bool:
        """虎威自身的CD是否就绪"""
        if self.last_active_tick == 0:
            return True
        if self.sim_instance is None:
            return True
        return self.last_active_tick + self.cd < self.sim_instance.tick

    @property
    def occupied(self) -> bool:
        """虎威是否被占用（包括旋转）"""
        return self.occupied_origin is not None

    def update_occupied_origin(self, origin: SkillNode, tick: int):
        """更新虎威的占用源"""
        self.occupied_origin = origin
        self.occupied_state_update_tick = tick
        if JUFUFU_REPORT:
            self.sim_instance.schedule_data.change_process_state()
            print(f"虎威被{self.occupied_origin.skill_tag}占用！占用状态将于{self.occupied_state_update_tick + self.occupied_origin.skill.ticks}tick结束！")

    def release(self):
        """虎威置空自身被占用状态的方法"""
        self.occupied_origin = None
        if JUFUFU_REPORT:
            self.sim_instance.schedule_data.change_process_state()
            print(f"虎威的占用状态已结束！")

    def check_myself(self):
        """虎威自检，内置CD啥的，若条件满足则run_myself，每个tick执行一次。"""
        if self.sim_instance is None:
            self.sim_instance = self.char.sim_instance

        # 首先检测自身是否处于被占用状态
        if self.occupied:
            return
        # 然后检测自身是否处于旋转状态——更改旋转状态的逻辑不在这里，那是触发器Buff负责的；
        if self.spinning_state:
            self.spawn_action(signal=1)
        # 如果前面都不满足，则进入普攻分支的判断；
        else:
            if self.ready:
                self.spawn_action(signal=0)

    def spawn_action(self, signal: int):
        """
        根据传入的更新信号做出决策——到底是打平A还是打连携技或是其他，信号：
        0：普通攻击
        1：高速旋转攻击
        2：连携技
        """
        tick = self.sim_instance.tick
        if signal == 0:
            self.last_active_tick = tick
            if JUFUFU_REPORT:
                self.sim_instance.schedule_data.change_process_state()
                print(f"虎威释放一次普通攻击！")

    def update_occupied_state(self, skill_node: SkillNode):
        """把外部传入的skill_node做筛选，并且更新虎威的占用状态"""
        if skill_node.skill_tag in self.occupied_skill_list:
            self.update_occupied_origin(skill_node, tick=self.sim_instance.tick)




