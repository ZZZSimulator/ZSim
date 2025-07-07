import math

from zsim.define import VIVIAN_REPORT
from zsim.sim_progress.ScheduledEvent.Calculator import (
    Calculator as Cal,
)
from zsim.sim_progress.ScheduledEvent.Calculator import (
    MultiplierData as Mul,
)

from .. import Buff, JudgeTools, check_preparation


class VivianCinema6TriggerRecord:
    def __init__(self):
        self.char = None
        self.preload_data = None
        self.last_update_node = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None
        self.cinema_ratio = None
        self.guard_feather = None

    @property
    def c6_ratio(self):
        return self.guard_feather * 0.8


class VivianCinema6Trigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """薇薇安的核心被动触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xeffect = self.special_effect_logic
        self.ANOMALY_RATIO_MUL = {
            0: 0.0075,
            1: 0.08,
            2: 0.0108,
            3: 0.032,
            4: 0.0615,
            5: 0.0108,
        }

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["薇薇安"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = VivianCinema6TriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        薇薇安的核心被动触发器：
        触发机制为：全队任意角色触发属性异常的第一跳时，构造一个新的属性异常放到Evenlist中
        """
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node不是SkillNode类型！"
            )

        if skill_node.skill_tag != "1331_SNA_2":
            return False
        if not self.record.enemy.dynamic.is_under_anomaly:
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    " APL警告：怪物没异常你打什么SNA_2！豆子全没了吧傻子！"
                )
        if self.record.last_update_node is None:
            self.c6_pre_active(skill_node)
            return True
        else:
            if skill_node.UUID != self.record.last_update_node.UUID:
                self.c6_pre_active(skill_node)
                return True
        return False

    def c6_pre_active(self, skill_node):
        self.record.last_update_node = skill_node
        guard_feather_cost = min(self.record.char.feather_manager.guard_feather, 5)
        if VIVIAN_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"6画触发器：检测到【悬落】，即将消耗全部护羽！消耗前的资源情况为：{self.record.char.get_special_stats()}"
            )
        self.record.guard_feather = guard_feather_cost
        self.record.char.feather_manager.guard_feather = 0
        self.record.char.feather_manager.c1_counter += guard_feather_cost
        while self.record.char.feather_manager.c1_counter >= 4:
            self.record.char.feather_manager.c1_counter -= 4
            self.record.char.feather_manager.flight_feather = min(
                self.record.char.feather_manager.flight_feather + 1, 5
            )
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    f"6画触发器：因6画触发、联动1画，恢复一点飞羽！当前资源情况为：{self.record.char.get_special_stats()}"
                )

    def special_effect_logic(self, **kwargs):
        """当Xjudge检测到AnomalyBar传入时通过判定，并且执行xeffect"""
        self.check_record_module()
        self.get_prepared(
            char_CID=1361,
            preload_data=1,
            dynamic_buff_list=1,
            enemy=1,
            sub_exist_buff_dict=1,
        )
        from zsim.sim_progress.anomaly_bar import AnomalyBar

        get_result = self.record.enemy.dynamic.get_active_anomaly()
        if not get_result:
            self.record.char.feather_manager.update_myself(c6_signal=True)
            if VIVIAN_REPORT:
                self.buff_instance.sim_instance.schedule_data.change_process_state()
                print(
                    "6画触发器：在怪物没有异常的情况下打了【悬落】，虽然不能触发额外的异放，但是依然可以进行羽毛转化！"
                )
        active_anomaly_bar = get_result[0]
        copyed_anomaly = AnomalyBar.create_new_from_existing(active_anomaly_bar)
        # copyed_anomaly = self.record.last_update_anomaly
        event_list = JudgeTools.find_event_list(
            sim_instance=self.buff_instance.sim_instance
        )
        mul_data = Mul(
            self.record.enemy, self.record.dynamic_buff_list, self.record.char
        )
        ap = Cal.AnomalyMul.cal_ap(mul_data)
        from zsim.sim_progress.anomaly_bar.CopyAnomalyForOutput import (
            DirgeOfDestinyAnomaly,
        )

        dirge_of_destiny_anomaly = DirgeOfDestinyAnomaly(
            copyed_anomaly,
            active_by="1331",
            sim_instance=self.buff_instance.sim_instance,
        )
        ratio = self.ANOMALY_RATIO_MUL.get(copyed_anomaly.element_type)
        if self.record.cinema_ratio is None:
            self.record.cinema_ratio = 1 if self.record.char.cinema < 2 else 1.3
        final_ratio = (
            math.floor(ap / 10)
            * ratio
            * self.record.cinema_ratio
            * self.record.c6_ratio
        )
        dirge_of_destiny_anomaly.anomaly_dmg_ratio = final_ratio
        dirge_of_destiny_anomaly.current_ndarray = (
            dirge_of_destiny_anomaly.current_ndarray
            / dirge_of_destiny_anomaly.current_anomaly
        )
        event_list.append(dirge_of_destiny_anomaly)
        if VIVIAN_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"6画触发器：触发额外异放！本次触发消耗额外护羽数量为：{self.record.guard_feather}，当前资源情况为：{self.record.char.get_special_stats()}"
            )
        self.record.guard_feather = 0
        self.record.char.feather_manager.update_myself(c6_signal=True)
