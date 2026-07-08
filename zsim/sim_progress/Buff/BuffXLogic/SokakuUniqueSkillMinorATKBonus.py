from .. import Buff, JudgeTools, check_preparation
from ..JudgeTools import build_preparation_context_from_buff
from ._preparation_helpers import ensure_owner_template_record, prepare_with_context


class SokakuUniqueSkillMinorATKRecord:
    def __init__(self):
        self.char = None
        self.sub_exist_buff_dict = None


class SokakuUniqueSkillMinorATKBonus(Buff.BuffLogic):
    """
    这里是苍角的核心被动 1，核心被动1的触发无需复杂代码控制，
    只要释放了展旗，就会判定通过。
    但是，具体的层数，却是要根据苍角的面板攻击力实时调取的。
    """

    def __init__(self, buff_instance):
        super().__init__(buff_instance)
        self.buff_instance: Buff = buff_instance
        self.xstart = self.special_start_logic
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
            owner_name="苍角",
            record_factory=SokakuUniqueSkillMinorATKRecord,
            context_builder=build_preparation_context_from_buff,
        )

    def special_start_logic(self, **kwargs):
        """
        展旗发动时，应该检索当前角色的面板攻击力。
        """
        self.check_record_module()
        self.get_prepared(char_CID=1131, sub_exist_buff_dict=1)
        atk_now = self.record.char.statement.ATK
        count = min(atk_now * 0.2, 500)
        tick_now = JudgeTools.find_tick(sim_instance=self.buff_instance.sim_instance)
        self.buff_instance.simple_start(tick_now, self.record.sub_exist_buff_dict)
        self.buff_instance.dy.count = count
        self.buff_instance.update_to_buff_0(self.buff_0)
