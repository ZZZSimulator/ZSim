from zsim.define import VIVIAN_REPORT
from zsim.sim_progress.ScheduledEvent.Calculator import (
    Calculator as Cal,
)
from zsim.sim_progress.ScheduledEvent.Calculator import (
    MultiplierData as Mul,
)

from .. import Buff, JudgeTools, check_preparation


class VivianCorePassiveTriggerRecord:
    def __init__(self):
        self.char = None
        self.preload_data = None
        self.last_update_node = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None
        self.cinema_ratio = None


class VivianCorePassiveTrigger(Buff.BuffLogic):
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
            self.buff_0.history.record = VivianCorePassiveTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """
        薇薇安的核心被动触发器：
        触发机制为：落羽生花命中处于异常状态的目标时，构造一个新的属性异常放到Evenlist中
        """
        self.check_record_module()
        self.get_prepared(char_CID=1331, enemy=1)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取到的skill_node 不是SkillNode类型"
            )
        if skill_node.skill_tag != "1331_CoAttack_A":
            return False
        if not self.record.enemy.dynamic.is_under_anomaly():
            return False
        if self.record.last_update_node is None:
            self.record.last_update_node = skill_node
            return True
        else:
            if skill_node.UUID != self.record.last_update_node.UUID:
                self.record.last_update_node = skill_node
                return True
            else:
                return False

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
            raise ValueError(
                f"{self.buff_instance.ft.index}的xeffect函数中，enemy.get_active_anomlay函数返回空列表，说明此时没有异常。但是xjudge函数却放行了。"
            )
        active_anomaly_bar = get_result[0]
        copyed_anomaly = AnomalyBar.create_new_from_existing(active_anomaly_bar)
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
        """20250424参考波波獭视频，该倍率是每一点精通平滑收益，并非向下取整，故此调整模型，去掉floor。"""
        """final_ratio = math.floor(ap/10) * ratio * self.record.cinema_ratio"""
        final_ratio = ap / 10 * ratio * self.record.cinema_ratio
        dirge_of_destiny_anomaly.anomaly_dmg_ratio = final_ratio
        # dirge_of_destiny_anomaly.current_ndarray = (
        #     dirge_of_destiny_anomaly.current_ndarray
        #     / dirge_of_destiny_anomaly.current_anomaly
        # )
        event_list.append(dirge_of_destiny_anomaly)
        if VIVIAN_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                "核心被动：检测到【落羽生花】命中异常状态下的敌人，触发一次异放！！！"
            )

