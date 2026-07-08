from zsim.define import ASTRAYAO_REPORT

from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class AstraYaoCorePassiveAtkBonusRecord:
    def __init__(self):
        self.char = None
        self.core_passive_ratio = 0.35
        self.duration_added_per_active = 1200
        self.update_info_box = {}
        self.sub_exist_buff_dict = None


class AstraYaoCorePassiveAtkBonus(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """耀嘉音核心被动攻击力的xstart方法"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0: Buff | None = None
        self.record = None
        self.xstart = self.special_start_logic

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="耀嘉音",
            record_factory=AstraYaoCorePassiveAtkBonusRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_start_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1311, sub_exist_buff_dict=1)
        from zsim.sim_progress.Character import Character

        if not isinstance(self.record.char, Character):
            raise TypeError
        benifit = kwargs.get("benifit", None)
        if benifit is None:
            raise ValueError(f"{self.buff_instance.ft.index}的xstart函数并未获取到benifit参数")
        static_atk = self.record.char.statement.ATK
        count = min(static_atk * self.record.core_passive_ratio, self.buff_instance.ft.maxcount)
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if self.buff_0.dy.active and benifit in self.record.update_info_box:
            last_update_tick = self.record.update_info_box[benifit]["startticks"]
            if last_update_tick == find_tick(sim_instance=self.buff_instance.sim_instance):
                # print(f'已经检测到{benifit}角色在当前tick有过buff更新，所以不做重复更新！！！')
                return
            # last_update_duration = self.record.update_info_box[benifit]["endticks"] - last_update_tick
            last_update_end_tick = self.record.update_info_box[benifit]["endticks"]
            """如果本次buff更新的受益者曾在很久之前被加过buff，但是buff早就掉了，那么就当成第一次触发处理。"""
            if last_update_end_tick < tick:
                last_update_end_tick = tick
            self.buff_instance.simple_start(
                tick, self.record.sub_exist_buff_dict, no_start=1, no_count=1, no_end=1
            )
            self.buff_instance.dy.startticks = tick
            # self.buff_instance.dy.endticks = min(last_update_duration - tick + last_update_tick + 1200, self.buff_instance.ft.maxduration+tick)
            self.buff_instance.dy.endticks = min(
                last_update_end_tick + 1200, self.buff_instance.ft.maxduration + tick
            )
            # if self.buff_instance.dy.startticks > self.buff_instance.dy.endticks:
            #     print(self.buff_instance.dy.startticks, self.buff_instance.dy.endticks, benifit)
            #     print(self.record.update_info_box[benifit])
        else:
            self.buff_instance.simple_start(
                tick, self.record.sub_exist_buff_dict, no_count=1, no_end=1
            )
            self.buff_instance.dy.endticks = tick + self.record.duration_added_per_active
        self.buff_instance.dy.count = count
        # if self.buff_instance.dy.startticks > self.buff_instance.dy.endticks:
        #     print(self.buff_instance.dy.startticks, self.buff_instance.dy.endticks, benifit)
        self.record.update_info_box[benifit] = {
            "startticks": tick,
            "endticks": self.buff_instance.dy.endticks,
            "count": count,
        }
        self.buff_instance.update_to_buff_0(self.buff_0)
        if ASTRAYAO_REPORT:
            self.buff_instance.sim_instance.schedule_data.change_process_state()
            print(
                f"核心被动触发器激活！成功为{benifit}角色添加攻击力buff（{count}点）！Buff的时间节点为：{self.buff_instance.dy.startticks}--{self.buff_instance.dy.endticks}"
            )
