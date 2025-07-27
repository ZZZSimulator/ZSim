from .. import Buff, JudgeTools, check_preparation
from zsim.define import YUZUHA_REPORT
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class YuzuhaCinema2TriggerRecord:
    def __init__(self):
        self.char = None
        self.allowed_skill_tag_list = ["1411_E_EX_A", "1411_E_EX_B", "1411_Q"]
        self.skill_node_be_changed = None
        self.cd = 1200
        self.last_update_tick = None
        self.enemy = None


class YuzuhaCinema2Trigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaCinema2TriggerRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柚叶"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YuzuhaCinema2TriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1411, enemy=1)
        if self.record.skill_node_be_changed is not None:
            raise ValueError("【浮波柚叶2画触发器】存在尚未处理的更新信号！！")
        if self.record.enemy.dynamic.stun:
            return False
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.skill_tag not in self.record.allowed_skill_tag_list:
            return False
        if not self.ready:
            return False
        tick = self.buff_instance.sim_instance.tick
        if not skill_node.is_last_hit(tick=tick):
            return False
        else:
            self.record.skill_node_be_changed = skill_node
            return True

    @property
    def ready(self):
        if self.record.last_update_tick is None:
            return True
        tick = self.buff_instance.sim_instance.tick
        if tick - self.record.last_update_tick > self.record.cd:
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1411)
        if self.record.skill_node_be_changed is None:
            raise ValueError("【浮波柚叶2画触发器】未发现更新信号！！")
        skill_node: "SkillNode" = self.record.skill_node_be_changed
        skill_node.force_qte_trigger = True
        if YUZUHA_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"【柚叶2画】检测到{skill_node.skill_tag}的重攻击即将命中非失衡敌人！修改参数使其能够触发QTE！"
            )
        self.record.skill_node_be_changed = None
        self.record.last_update_tick = self.buff_instance.sim_instance.tick
