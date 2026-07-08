from typing import TYPE_CHECKING, Any, Sequence

if TYPE_CHECKING:
    from zsim.sim_progress.calculation.calculator import CalculatorBuffBonusReadContext
    from zsim.sim_progress.Character import Character
    from zsim.sim_progress.ScheduledEvent.buff_runtime import BuffRuntimeReadPort


class SPUpdateData:
    def __init__(
        self,
        char_obj: "Character",
        dynamic_buff: dict[str, Sequence[Any]] | None = None,
        *,
        runtime_view: "BuffRuntimeReadPort | None" = None,
        sim_instance: Any | None = None,
    ):
        """更新角色SP时的专用数据结构，仅用于传递角色的静态与动态的能量自动回复效率"""
        self.char_name = char_obj.NAME
        self.static_sp_regen: float = char_obj.statement.sp_regen
        bonus_context = self.__create_bonus_context(
            char_name=self.char_name,
            dynamic_buff=dynamic_buff,
            runtime_view=runtime_view,
            sim_instance=sim_instance,
        )
        self.dynamic_sp_regen: tuple[float, float] = self.__cal_dynamic_sp_regen(bonus_context)

    @staticmethod
    def __create_bonus_context(
        *,
        char_name: str,
        dynamic_buff: dict[str, Sequence[Any]] | None,
        runtime_view: "BuffRuntimeReadPort | None",
        sim_instance: Any | None,
    ) -> "CalculatorBuffBonusReadContext":
        from zsim.sim_progress.calculation.calculator import (
            create_calculator_buff_bonus_context,
            create_calculator_buff_bonus_context_from_runtime_view,
        )

        if runtime_view is not None:
            return create_calculator_buff_bonus_context_from_runtime_view(
                runtime_view=runtime_view,
                beneficiary=char_name,
                sim_instance=sim_instance,
            )
        active_buffs = () if dynamic_buff is None else dynamic_buff.get(char_name, ())
        return create_calculator_buff_bonus_context(
            active_buffs=active_buffs,
            sim_instance=sim_instance,
            char_name=char_name,
        )

    @staticmethod
    def __cal_dynamic_sp_regen(bonus_context: "CalculatorBuffBonusReadContext"):
        from zsim.sim_progress.calculation.calculator import (
            get_calculator_buff_attribute_reader_service,
        )

        buff_bonus: dict = (
            get_calculator_buff_attribute_reader_service().calculate_buff_total_bonus(bonus_context)
        )
        dynamic_sp_regen = buff_bonus.get("能量自动恢复", 0) + buff_bonus.get("局内能量自动恢复", 0)
        dynamic_sp_gain_ratio = buff_bonus.get("局内能量获得效率", 0)
        return dynamic_sp_regen, dynamic_sp_gain_ratio

    def get_sp_regen(self) -> float:
        sp_regen = (self.static_sp_regen + self.dynamic_sp_regen[0]) * (
            self.dynamic_sp_regen[1] + 1
        )
        return sp_regen


class ScheduleRefreshData:
    def __init__(
        self,
        *,
        sp_target: tuple[str] | None = None,
        sp_value: float | int = 0,
        decibel_target: tuple[str] | None = None,
        decibel_value: float | int = 0,
        **kwargs,
    ):
        # 避免可变默认参数
        self.sp_target: tuple[str] = sp_target if sp_target is not None else ("",)
        self.decibel_target: tuple[str] = decibel_target if decibel_target is not None else ("",)

        # 类型检查和异常处理
        if not isinstance(sp_value, (float, int)):
            raise TypeError("sp_value 必须是数字")
        if not isinstance(decibel_value, (float, int)):
            raise TypeError("decibel_value 必须是数字")

        self.sp_value = sp_value
        self.decibel_value = decibel_value

        # 输入验证
        if not self.sp_target or not all(isinstance(item, str) for item in self.sp_target):
            raise ValueError("sp_target 必须是非空字符串元组")
        if not self.decibel_target or not all(
            isinstance(item, str) for item in self.decibel_target
        ):
            raise ValueError("decibel_target 必须是非空字符串元组")

        allowed_kwargs = {
            "additional_param1",
            "additional_param2",
        }  # 根据实际情况定义允许的额外参数
        for key, value in kwargs.items():
            if key in allowed_kwargs:
                setattr(self, key, value)
            else:
                raise ValueError(f"Unexpected keyword argument: {key}")
