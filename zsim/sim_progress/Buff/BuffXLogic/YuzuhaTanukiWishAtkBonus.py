from .. import Buff, JudgeTools, check_preparation
from ....define import YUZUHA_REPORT


class YuzuhaTanukiWishAtkBonusRecord:
    def __init__(self):
        self.char = None
        self.core_passive_ratio = 0.4
        self.sub_exist_buff_dict = None


class YuzuhaTanukiWishAtkBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record: YuzuhaTanukiWishAtkBonusRecord | None = None

    def get_prepared(self, **kwargs):
        return check_preparation(
            buff_instance=self.buff_instance, buff_0=self.buff_0, **kwargs
        )

    def check_record_module(self):
        if self.buff_0 is None:
            self.buff_0 = JudgeTools.find_exist_buff_dict(
                sim_instance=self.buff_instance.sim_instance
            )["柚叶"][self.buff_instance.ft.index]
        if self.buff_0.history.record is None:
            self.buff_0.history.record = YuzuhaTanukiWishAtkBonusRecord()
        self.record = self.buff_0.history.record

    def special_hit_logic(self, **kwargs):  
        """buff激活时，根据柚叶的场外攻击力计算层数，"""
        self.check_record_module()
        self.get_prepared(char_CID=1411, sub_exist_buff_dict=1)
        tick = self.buff_instance.sim_instance.tick
        static_atk = self.record.char.statement.ATK
        count = min(
            static_atk * self.record.core_passive_ratio, self.buff_instance.ft.maxcount
        )
        self.buff_instance.simple_start(timenow=tick, sub_exist_buff_dict=self.record.sub_exist_buff_dict, no_count=1)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(buff_0=self.buff_0)
        if YUZUHA_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(f"【狸之愿】柚叶核心被动触发！柚叶场外站街攻击力为{static_atk:.2f}点，【狸之愿】为队友提供{count}点攻击力！")
