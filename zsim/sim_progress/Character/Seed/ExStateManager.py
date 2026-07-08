from typing import TYPE_CHECKING

from ....define import SEED_REPORT
from ..character import Character

if TYPE_CHECKING:
    from zsim.sim_progress.Preload import SkillNode


class SeedEXState:
    """席德强化E释放的**当前**状态"""

    IDLE = "idle"  # 未开始强化E
    FIRST_CAST = "first"  # 第一段 (E_EX_0)
    LOOPING = "looping"  # 循环段 (E_EX_1)
    INTRUPTED = "interrupted"  # 中途打断 (E_EX_2)
    FINISH = "finish"  # 完整结束(SNA_1)


class SeedEXStateManager:
    def __init__(self, char_instance: Character):
        self.char = char_instance
        assert self.char.NAME == "席德", (
            f"SeedEXStateManager 仅支持席德, 当前角色为 {self.char.NAME}"
        )
        from . import Seed

        assert type(self.char) is Seed
        self.e_ex_max_repeat_times: int = 10 if self.char.cinema < 2 else 20
        self.allowed_list = ["1461_E_EX_0", "1461_E_EX_1", "1461_E_EX_2", "1461_SNA_1"]
        self._e_ex_state = SeedEXState.IDLE
        self.repeat_count = 0  # 当前E_EX_1的重复次数

        self.state_mapping = {
            SeedEXState.IDLE: "1461_E_EX_0",
            SeedEXState.FIRST_CAST: "1461_E_EX_1",
            SeedEXState.LOOPING: "1461_E_EX_1",
            SeedEXState.INTRUPTED: "1461_E_EX_0",
            SeedEXState.FINISH: "1461_SNA_1",
        }
        self.cinema_2_buff_index = "Buff-角色-席德-影画-2画-耗能转化增伤"

    @property
    def e_ex_state(self) -> str:
        return self._e_ex_state

    @e_ex_state.setter
    def e_ex_state(self, value: SeedEXState):
        """设置强化E释放的当前状态"""

        self._e_ex_state = value

    def update_ex_state(self, skill_node: "SkillNode"):
        """根据当前状态更新EX状态"""

        # 由于非主动动作永远不可能在在强化E期间插入，但是额外伤害类技能是可以的，所以这里我们排除一下，避免干扰误触断言。
        if skill_node.is_additional_damage:
            return
        if skill_node.skill_tag in self.allowed_list:
            if skill_node.skill_tag == "1461_E_EX_0":
                assert self.e_ex_state not in [
                    SeedEXState.LOOPING,
                    SeedEXState.FIRST_CAST,
                ], f"席德的强化E释放状态状态错误, 当前状态为 {self.e_ex_state}"
                self.e_ex_state = SeedEXState.FIRST_CAST
                self.repeat_count = 0  # 在检测到起手式时重置重复次数
            elif skill_node.skill_tag == "1461_E_EX_1":
                assert self.e_ex_state not in [
                    SeedEXState.IDLE,
                    SeedEXState.INTRUPTED,
                    SeedEXState.FINISH,
                ], f"席德的强化E释放状态状态错误, 当前状态为 {self.e_ex_state}"
                assert self.repeat_count < self.e_ex_max_repeat_times, (
                    f"席德的强化E释放状态状态错误, 重复次数超过最大次数 {self.e_ex_max_repeat_times}"
                )
                self.repeat_count += 1
                self.e_ex_state = (
                    SeedEXState.LOOPING
                    if self.repeat_count < self.e_ex_max_repeat_times
                    else SeedEXState.FINISH
                )
            elif skill_node.skill_tag == "1461_E_EX_2":
                assert self.e_ex_state in [
                    SeedEXState.LOOPING,
                    SeedEXState.FIRST_CAST,
                ], f"席德的强化E释放状态状态错误, 当前状态为 {self.e_ex_state}"
                assert self.repeat_count < self.e_ex_max_repeat_times, (
                    f"席德的强化E释放状态状态错误, 既然打出了E_EX_2就说明提前打断了强化E释放，此时释放次数（{self.repeat_count}次）应小于最大次数{self.e_ex_max_repeat_times}"
                )
                # print(22222, f"{self.char.sim_instance.tick}tick：检测到1461_E_EX_2，强化E状态从{self.e_ex_state}切换到{SeedEXState.INTRUPTED}")
                self.e_ex_state = SeedEXState.INTRUPTED

            elif skill_node.skill_tag == "1461_SNA_1":
                if self.e_ex_state == SeedEXState.IDLE:
                    # 若是传入了第一段重击，同时强化E状态为IDLE，说明此次SNA_1和强化E连段无关，直接返回
                    return
                else:
                    assert self.e_ex_state in [
                        SeedEXState.FINISH,
                        SeedEXState.INTRUPTED,
                    ], f"席德的强化E释放状态状态错误, 当前状态为 {self.e_ex_state}"
                    self.e_ex_state = SeedEXState.IDLE
                    if self.char.cinema >= 2:
                        if SEED_REPORT:
                            self.char.sim_instance.schedule_data.change_process_state()
                            print(
                                f"【席德2画报告】检测到强化E结束，本次强化E共耗能{self.repeat_count * 5:.0f}点，将为本次自动衔接的 {skill_node.skill.skill_text} 提供{self.repeat_count * 5:.0f}%的增伤！"
                            )
                        from zsim.sim_progress.Buff.BuffAddStrategy import buff_add_strategy

                        benefit_list = ["席德"]
                        buff_add_strategy(
                            self.cinema_2_buff_index,
                            benifit_list=benefit_list,
                            specified_count=self.repeat_count,
                            sim_instance=self.char.sim_instance,
                        )

        else:
            assert self.e_ex_state not in [
                SeedEXState.LOOPING,
                SeedEXState.FIRST_CAST,
            ], f"在传入其他无关技能时，席德的强化E状态处于未结算的情况，当前状态为{self.e_ex_state}"
            if self.e_ex_state in [SeedEXState.FINISH, SeedEXState.INTRUPTED]:
                self.e_ex_state = SeedEXState.IDLE

    def action_replacement_handler(self, action: str):
        """根据当前强化E状态，转换为对应强化E技能index"""
        state = self.e_ex_state
        # 对于不是席德的动作，直接返回
        if "1461" not in action:
            return action
        if action in ["1461_E_EX_0", "1461_E_EX_1", "1461_E_EX_2"]:
            action = "1461_E_EX"
        if action == "1461_E_EX":
            result = self.state_mapping[state]
            # print(f"{self.char.sim_instance.tick}tick：强化E状态为{state}，指令{action}被替换为了{result}")
            return result
        else:
            if state in [SeedEXState.LOOPING, SeedEXState.FIRST_CAST]:
                # print(1111, f"在{self.char.sim_instance.tick}tick   指令{action}被替换为了1461_E_EX_2")
                return "1461_E_EX_2"
            else:
                return action
