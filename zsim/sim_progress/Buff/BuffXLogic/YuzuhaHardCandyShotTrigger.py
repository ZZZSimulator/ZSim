from .. import Buff, JudgeTools, check_preparation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...Preload import SkillNode
    from ...Character.Yuzuha import Yuzuha


class YuzuhaHardCandyShotTriggerRecord:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None
        self.cd = 480
        self.last_update_tick = None
        self.update_signal = None


class YuzuhaHardCandyShotTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """硬糖射击触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

    def get_prepared(self, **kwargs):
        return check_preparation(buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs)

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柚叶"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YuzuhaHardCandyShotTriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """队友的攻击命中时放行"""
        self.check_record_module()
        self.get_prepared(char_CID=1411)
        skill_node: "SkillNode" = kwargs.get("skill_node")
        # 筛选出队友的攻击命中
        if skill_node is None:
            return False
        if skill_node.char_name == self.record.char.NAME:
            return False
        tick = self.buff_instance.sim_instance.tick
        if not skill_node.is_hit_now(tick=tick):
            return False

        char: "Yuzuha" = self.record.char
        # 先保证角色有空
        if not char.is_available(tick=tick):
            return False
        # 再保证甜度点足够
        if char.get_resources()[1] < 1:
            return False
        else:
            if self.ready:
                self.record.update_signal = skill_node
                return True
            return False

    def special_hit_logic(self, **kwargs):
        """触发硬糖射击，首先要进行一次simple_start保证触发内置CD，然后再执行业务逻辑"""
        self.check_record_module()
        self.get_prepared(char_CID=1411, sub_exist_buff_dict=1)
        char: "Yuzuha" = self.record.char
        tick = self.buff_instance.sim_instance.tick
        self.buff_instance.simple_start(
            timenow=tick, sub_exist_buff_dict=self.record.sub_exist_buff_dict
        )
        char.spawn_hard_candy_shot(update_signal=self.record.update_signal)
        self.record.last_update_tick = tick
        self.record.update_signal = None

    @property
    def ready(self):
        if self.record.last_update_tick is None:
            return True
        if self.buff_instance.sim_instance.tick - self.record.last_update_tick > self.record.cd:
            return True
        else:
            return False
