from typing import TYPE_CHECKING

from .. import Buff, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._buff_record_base_class import BuffRecordBaseClass as BRBC

if TYPE_CHECKING:
    pass


class AliceCinema6TriggerRecord(BRBC):
    def __init__(self):
        super().__init__()
        self.additional_attack_skill_tag = "1401_Cinema_6"  # 6画额外攻击的技能tag


class AliceCinema6Trigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.buff_0: "Buff | None" = None
        self.record: BRBC | None = None

    def get_prepared(self, **kwargs):
        preparation_context = build_preparation_context_from_buff(self.buff_instance)
        return check_preparation(
            buff_instance=self.buff_instance,
            buff_0=self.buff_0,
            preparation_context=preparation_context,
            **kwargs,
        )

    def check_record_module(self):
        if self.buff_0 is None:
            preparation_context = build_preparation_context_from_buff(self.buff_instance)
            self.buff_0 = preparation_context.find_sub_exist_buff_dict("爱丽丝")[
                self.buff_instance.ft.index
            ]
        assert self.buff_0 is not None, "buff_0不能为空"
        if self.buff_0.history.record is None:
            self.buff_0.history.record = AliceCinema6TriggerRecord()
        self.record = self.buff_0.history.record

    def special_judge_logic(self, **kwargs):
        """爱丽丝的6画额外攻击逻辑判定函数，只会在决胜状态可用时放行队友技能的命中事件"""
        self.check_record_module()
        self.get_prepared(char_CID=1401)
        assert self.record is not None, "记录模块未正确初始化，请检查函数"
        assert self.record.char is not None, "角色未正确初始化，请检查函数"
        from zsim.sim_progress.Character.Alice import Alice

        if not isinstance(self.record.char, Alice):
            raise TypeError("【爱丽丝6画触发器警告】初始化时获取的角色并非爱丽丝，请检查初始化逻辑")
        skill_node = kwargs.get("skill_node")
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        assert isinstance(skill_node, SkillNode), "skill_node必须为SkillNode类型"
        # 首先过滤掉自己的技能
        if skill_node.char_name == self.record.char.NAME:
            return False

        # 当爱丽丝不处于决胜状态时，不触发
        if not self.record.char.victory_state:
            # print(self.record.char.victory_state_update_tick, self.record.char.victory_state_attack_counter)
            return False
        # 过滤掉并非处于命中帧的技能
        if not skill_node.is_hit_now(tick=self.buff_instance.sim_instance.tick):
            return False
        else:
            if self.record.check_cd(tick_now=self.buff_instance.sim_instance.tick):
                return True
            else:
                return False

    def special_hit_logic(self, **kwargs):
        """爱丽丝6画额外攻击触发器的业务函数，主要负责调用角色方法，添加额外攻击的Preload事件"""
        self.check_record_module()
        self.get_prepared(char_CID=1401)
        assert self.record is not None, "记录模块未正确初始化，请检查函数"
        assert self.record.char is not None, "角色未正确初始化，请检查函数"
        from zsim.sim_progress.Character.Alice import Alice

        if not isinstance(self.record.char, Alice):
            raise TypeError("【爱丽丝6画触发器警告】初始化时获取的角色并非爱丽丝，请检查初始化逻辑")
        self.record.char.spawn_extra_attack()
        self.record.last_active_tick = self.buff_instance.sim_instance.tick
