from sim_progress.Character.utils.filters import _skill_node_filter
from sim_progress.Character.character import Character
from sim_progress.Preload import SkillNode
from define import JUFUFU_REPORT
from .HuweiManagerClass import HuweiManager
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class Jufufu(Character):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.momentum: int = 0   # 威势点数
        self.might: int = 0 if self.cinema < 1 else 100  # 威风点数，一影画及以上进场给100
        self.max_might: int = 200       # 威风点数上限
        self.max_momentum: int = 15     # 威势点数上限
        self.huwei_manager = HuweiManager(self)       # 虎威管理器

    def special_resources(self, *args, **kwargs) -> None:
        """橘福福的特殊资源模块的主函数"""
        skill_nodes: list[SkillNode] = _skill_node_filter(*args, **kwargs)
        tick = self.sim_instance.tick
        for node in skill_nodes:
            if self.additional_abililty_active:
                # 检查队友的技能，如果是大招，则触发反哺喧响值逻辑、
                self.decibel_refund(node)
            if node.char_name == self.NAME:
                pass
            # TODO: 检查自己的技能，修改威风数值

            """威风、威势来源，以及处理位置：
            Character处理
            1、强化E：80威风，3威势——发动时获得
            2、大招：100威风，6威势——发动时获得
            3、协同连携：-100威风，发动时结算
            4、支援突击：1威势，10秒内置CD，发动时获得
            
            Buff触发器处理——调用Character的内置方法。
            5、虎威普攻，20威风，命中时获得
            6、强化旋转的撞击：-1威势，25威风，命中时结算
            
            """

        else:
            """
            因为涉及到占用问题，所以每个tick应该让skill_node更新传入优先于虎威自检，
            因为在第Ntick抛出的动作会在第N + 1tick被执行，而如果每个tick虎威的自检前置，那么容易重复抛出，
            """
            self.huwei_manager.check_myself()

    def decibel_refund(self, node):
        """模拟橘福福反哺队友喧响值的逻辑"""
        if node.skill.trigger_buff_level == 6:
            char_obj: Character = node.skill.char_obj
            if char_obj.speicalty in ["命破", "强攻"]:
                from zsim.sim_progress.data_struct import ScheduleRefreshData
                target_name = char_obj.NAME
                decibel_value = 300
                refresh_data = ScheduleRefreshData(
                    decibel_target=(target_name,),
                    decibel_value=decibel_value,
                )
                sim_instance: "Simulator" = self.sim_instance
                event_list = sim_instance.schedule_data.event_list
                event_list.append(refresh_data)
                if JUFUFU_REPORT:
                    sim_instance.schedule_data.change_process_state()
                    print(f"检测到{target_name}释放大招{node.skill.skill_text}，为其恢复{decibel_value}点喧响值！")

    def update_might(self, might_change: int, update_from: SkillNode | str):
        """更改威风点数的函数"""
        self.might += might_change
        if self.might < 0:
            print(f"【{update_from.skill_tag if isinstance(update_from, SkillNode) else update_from}】企图消耗{might_change}点威风！{self.NAME}的威风值不足！请检查APL！") if JUFUFU_REPORT else None
            self.might = 0
        if self.might > self.max_might:
            print(f"{self.NAME}的威风点数溢出{self.might - self.max_might}点") if JUFUFU_REPORT else None
            self.might = self.max_might

    def get_resources(self, *args, **kwargs) -> tuple[str | None, int | float | None]:
        return "威风", self.might

    def get_special_stats(self, *args, **kwargs) -> dict:
        pass

