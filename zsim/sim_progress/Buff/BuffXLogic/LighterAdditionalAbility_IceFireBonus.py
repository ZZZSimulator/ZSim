from zsim.sim_progress.calculation.calculator import (
    create_calculator_runtime_read_context_from_sim_instance,
    get_calculator_buff_attribute_reader_service,
)

from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class LighterExtraSkillRecord:
    def __init__(self):
        self.char = None
        self.enemy = None
        self.dynamic_buff_list = None
        self.sub_exist_buff_dict = None
        self.real_count = 0


class LighterExtraSkill_IceFireBonus(Buff.BuffLogic):
    """
    这个buff的特性是：能叠20层，每层起码有1.25%冰火增伤。但是，每次层数更新时，都会检测冲击力，
    冲击力超过170的部分，都会以0.025%的数值增幅到这个1.25%的基础数值上。

    模型转换：
    以0.25%为一层，本buff最多300层。
    buff本身层数分为两种，一种为虚层（fake_count），另一种为实层（real_count）。
    实层根据命中次数，每次5层（共1.25%）稳定增加，每次实层更新后（self.update_to_buff0，该函数无法调用，需要手动)
    那么有效叠加次数：hit_count = real_count / 5，而且这个一定是int。
    根据当前冲击力超过170的部分，算出每个effect_count所享受的虚层增幅fake_count_delta : （当前冲击力-170）/10，该数值可以是个小数
    实层传回buff_0的专用字段 buff.history.real_count 保存，下一次再拿。
    本tick的实际生效层数，也就是最后记录到self.dy.count 的算法是：
    self.dy.count = min(real_count + hit_count * fake_count_delta, 300)
    下一个ticks，虚层清空，重新计算，实层重新从buff_0拿过来\
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        # 初始化特定逻辑
        self.xhit = self.special_hit_logic
        self.buff_0 = None
        self.record = None

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
            owner_name="莱特",
            record_factory=LighterExtraSkillRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_hit_logic(self, **kwargs):
        self.check_record_module()
        self.get_prepared(char_CID=1161, enemy=1, sub_exist_buff_dict=1)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        buff_i = self.buff_instance
        buff_i.simple_start(tick_now, self.record.sub_exist_buff_dict)

        # 由于buff.dy.count的最终修改逻辑是直接赋值，不涉及累加。所以这里还原simple_start的步骤应该是多余的。
        # buff_i.dy.count -= buff_i.ft.step

        """
        先处理real_count的逻辑，最多100层（叠加20次）
        只要该模块执行了，那就说明又命中了一次，自然要+5层。
        但是这里用作计算的层数，不能来自simple_start之后的buff.dy.count，
        而应该是来自于record.real_count。
        这一步实现了命中叠加最基本层数，并且实时更新到realcount中。
        """
        real_count = min(self.record.real_count + buff_i.ft.step, 100)
        self.record.real_count = real_count

        # 计算实时冲击力
        context = create_calculator_runtime_read_context_from_sim_instance(
            sim_instance=self.buff_instance.sim_instance,
            enemy=self.record.enemy,
            character=self.record.char,
        )
        reader_service = get_calculator_buff_attribute_reader_service()
        stun_value = reader_service.read_impact(context)

        # 计算虚层
        fake_count_delta = max((stun_value - 170) / 10, 0)
        sum_fake_count = real_count / 5 * fake_count_delta

        # 计算等效的实际生效层数
        buff_i.dy.count = min(real_count + sum_fake_count, 300)
        buff_i.update_to_buff_0(self.buff_0)
        # print('buff_i：', main_module.tick, buff_i.dy.active, buff_i.dy.startticks, buff_i.dy.endticks, real_count, sum_fake_count)
        # print('buff_0：', buff_0.dy.active, buff_0.dy.startticks, buff_0.dy.endticks, buff_0.history.real_count)
