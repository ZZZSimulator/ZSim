from .. import Buff, check_preparation, find_tick
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class VivianFeatherTriggerRecord:
    def __init__(self):
        self.char = None
        self.last_update_node = None


class VivianFeatherTrigger(Buff.BuffLogic):
    def __init__(self, buff_instance):
        """管理薇薇安羽毛更新的触发器"""
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.buff_0 = None
        self.record = None
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic

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
            owner_name="薇薇安",
            record_factory=VivianFeatherTriggerRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """检测到最后一跳时放行"""
        self.check_record_module()
        self.get_prepared(char_CID=1331)
        skill_node = kwargs.get("skill_node", None)
        if skill_node is None:
            return False
        from zsim.sim_progress.Preload import SkillNode

        if not isinstance(skill_node, SkillNode):
            raise TypeError(
                f"{self.buff_instance.ft.index}的xjudge函数获取的skill_node不是SkillNode类型"
            )

        # 过滤掉不是自己的skill_node
        if "1331" not in skill_node.skill_tag:
            return False

        # 放行所有正处于最后一跳的skill_node
        tick = find_tick(sim_instance=self.buff_instance.sim_instance)
        if skill_node.loading_mission.is_last_hit(tick):
            self.record.last_update_node = skill_node
            return True
        else:
            return False

    def special_hit_logic(self, **kwargs):
        """只要触发器放行了，那么special_hit就一定会执行，执行一次后，把record清空即可。"""
        self.check_record_module()
        self.get_prepared(char_CID=1331)
        self.record.char.feather_manager.update_myself(self.record.last_update_node)
        self.record.last_update_node = None
