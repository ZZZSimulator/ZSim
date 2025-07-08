from typing import TYPE_CHECKING

from zsim.define import YIXUAN_REPORT

from .. import Buff, JudgeTools, check_preparation

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class YixuanCinema4TranquilityRecord:
    def __init__(self):
        self.char = None
        self.update_signal = None
        self.sub_exist_buff_dict = None
        self.c4_counter = 0  # 静心层数
        self.max_c4_count = 2


class YixuanCinema4Tranquility(Buff.BuffLogic):
    """仪玄4画的静心判定逻辑"""

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.xexit = self.special_exit_logic
        self.buff_0 = None
        self.record: YixuanCinema4TranquilityRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["仪玄"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YixuanCinema4TranquilityRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """仪玄4画的复杂逻辑，当传入技能是仪玄的大招时，叠层；当传入的技能是凝云术时，消耗层数。"""
        self.check_record_module()
        self.get_prepared(char_CID=1371)
        skill_node: "SkillNode | None" = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        tick = self.buff_instance.sim_instance.tick
        if skill_node.char_name != "仪玄":
            return False
        if skill_node.skill.trigger_buff_level == 6:
            # 发动大招时叠层
            if skill_node.preload_tick != tick:
                return False
            if self.record.update_signal is not None:
                raise ValueError(
                    f"{self.buff_instance.ft.index}的Xjudge函数的【大招分支】发现record中存在尚未处理的更新信号：{self.record.update_signal}！"
                )
            self.record.update_signal = 0
            return True
        else:
            # 检测到第二次墨烬影结束消层
            if skill_node.skill_tag == "1371_E_EX_B_3":
                if skill_node.end_tick != tick:
                    return False
                if self.record.update_signal is not None:
                    raise ValueError(
                        f"{self.buff_instance.ft.index}的Xjudge函数的【凝云术分支】发现record中存在尚未处理的更新信号：{self.record.update_signal}！"
                    )
                self.record.update_signal = 1
                return True
        return False

    def special_effect_logic(self, **kwargs):
        """4画的特殊生效逻辑，它根据record中的更新信号（update_signal），有两种模式，一种是叠层，每一种则是消层"""
        self.check_record_module()
        self.get_prepared(char_CID=1371, sub_exist_buff_dict=1)
        if self.record.update_signal is None:
            raise ValueError(
                f"{self.buff_instance.ft.index}的Xeffect函数执行时，并未检测到有效的更新信号！"
            )
        sim = self.buff_instance.sim_instance
        self.buff_instance.simple_start(
            timenow=sim.tick,
            sub_exist_buff_dict=self.record.sub_exist_buff_dict,
            no_count=1,
        )
        if self.record.update_signal == 0:
            self.record.c4_counter = min(
                self.record.c4_counter + 1, self.record.max_c4_count
            )
            self.buff_instance.dy.count = self.record.c4_counter
            if YIXUAN_REPORT:
                print(
                    f"4画：检测到仪玄释放大招，为仪玄叠加一层静心，当前的静心层数为：{self.record.c4_counter}"
                )
                self.buff_instance.sim_instance.schedule_data.change_process_state()
        elif self.record.update_signal == 1:
            # 经过实测，4画在消耗时会一次性消耗全部层数。
            if self.record.c4_counter != 0:
                if YIXUAN_REPORT:
                    print(
                        f"4画：检测到仪玄释放凝云术，本次凝云术消耗{self.record.c4_counter}层静心！"
                    )
                    self.buff_instance.sim_instance.schedule_data.change_process_state()
                self.record.c4_counter = 0
                self.buff_instance.dy.count = self.record.c4_counter
        else:
            raise ValueError(f"无法解析的更新信号！{self.record.update_signal}")
        self.buff_instance.update_to_buff_0(self.buff_0)
        self.record.update_signal = None

    def special_exit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1371)
        if self.record.c4_counter == 0:
            if YIXUAN_REPORT:
                print("4画：静心层数耗尽！Buff消退！")
                self.buff_instance.sim_instance.schedule_data.change_process_state()
            return True
        else:
            return False
