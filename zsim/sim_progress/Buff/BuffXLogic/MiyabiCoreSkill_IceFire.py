from typing import TYPE_CHECKING, Any

from zsim.sim_progress import Preload
from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)
from zsim.sim_progress.data_struct.schedule_dispatch import (
    ScheduledEventEmitter,
    ScheduledEventEmitterProvider,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context
from .enemy_debuff_mirror_read import MiyabiFrostburnDebuffMirrorReader
from .enemy_edge_state_read import read_enemy_frost_frostbite_edge_state

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class MiyabiCoreSkillIF:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None
        self.dynamic_buff_list = None
        self.last_frostbite = False
        self.enemy = None
        self.action_stack = None


class MiyabiCoreSkill_IceFire(Buff.BuffLogic):
    """
    该buff是雅的核心被动中的【冰焰】，冰焰在判断TrigerBuffLevel的同时，
    还需要检索当前enemy_debuff_list中是否含有【霜灼】，如果有就返回False
    """

    def __init__(
        self,
        buff_instance,
        scheduled_event_emitter_provider: ScheduledEventEmitterProvider | None = None,
    ):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self._scheduled_event_emitter_provider = (
            scheduled_event_emitter_provider
            or ScheduledEventEmitterProvider.from_sim_instance_getter(
                lambda: self.buff_instance.sim_instance
            )
        )
        self.xjudge = self.special_judge_logic
        self.xhit = self.special_hit_logic
        self.xexit = self.special_exit_logic
        self.buff_0: Any = None
        self.record: Any = None

    def get_prepared(self, **kwargs):
        return prepare_with_context(
            self,
            check_preparation_func=check_preparation,
            context_builder=build_preparation_context_from_buff,
            **kwargs,
        )

    def _scheduled_event_emitter(self) -> ScheduledEventEmitter:
        return self._scheduled_event_emitter_provider.create_emitter()

    def check_record_module(self):
        ensure_owner_template_record(
            self,
            owner_name="雅",
            record_factory=MiyabiCoreSkillIF,
            context_builder=build_preparation_context_from_buff,
        )

    def special_judge_logic(self, **kwargs):
        """
        这个复杂判断逻辑需要同时检索当前技能的element_type，
        以及enemy的debuff_list有没有霜灼，
        两者都通过，才会return True
        """
        self.check_record_module()
        self.get_prepared(char_CID=1091, enemy=1, action_stack=1)
        enemy = self.record.enemy
        debuff_reader = MiyabiFrostburnDebuffMirrorReader(enemy)
        skill_node: "SkillNode" = kwargs.get("skill_node")
        if skill_node is None:
            return False
        if skill_node.char_name != self.record.char.NAME:
            return False
        if skill_node.skill.element_type != 5:
            return False
        if debuff_reader.has_miyabi_frostburn_debuff():
            return False
        return True

    def special_exit_logic(self, **kwargs):
        """
        冰焰buff的退出机制是检测到霜寒的上升沿就退出
        """
        self.check_record_module()
        self.get_prepared(char_CID=1091, enemy=1)
        enemy = self.record.enemy
        frostbite_now = read_enemy_frost_frostbite_edge_state(enemy)
        if frostbite_now is None:
            frostbite_now = False

        frostbite_statement = [self.record.last_frostbite, frostbite_now]

        def mode_func(a, b):
            return a is False and b is True

        result = JudgeTools.detect_edge(frostbite_statement, mode_func)
        self.record.last_frostbite = frostbite_now
        # print(f'当前tick，冰焰退出情况：{result}')
        if result:
            skill_obj = self.record.char.skills_dict["1091_Core_Passive"]
            skill_node = Preload.SkillNode(skill_obj, 0)
            self._scheduled_event_emitter().emit_scheduled(skill_node)
            self.record.char.special_resources(skill_node)
        return result

    def special_hit_logic(self, **kwargs):
        """
        冰焰的生效机制是：根据当前的暴击率，得出当前的Buff层数。
        这个效果本应该是随动的，不需要buff判定通过才改变层数，
        但是如果buff判定不通过，那么烈霜伤害，该buff层数的变动就没有实际意义，
        """
        self.check_record_module()
        self.get_prepared(char_CID=1091, enemy=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        buff_i = self.buff_instance
        buff_i.simple_start(tick_now, self.record.sub_exist_buff_dict)
        buff_i.dy.count -= buff_i.ft.step

        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        crit_rate = reader_service.read_full_crit_rate(context)
        count = min(crit_rate, 0.8) * 100

        # print(crit_rate, count)
        buff_i.dy.count = min(count, self.buff_0.ft.maxcount)
        buff_i.update_to_buff_0(self.buff_0)
