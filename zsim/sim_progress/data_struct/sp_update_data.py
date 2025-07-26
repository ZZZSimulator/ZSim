from typing import TYPE_CHECKING, Generator

from .data_analyzer import cal_buff_total_bonus

if TYPE_CHECKING:
    from zsim.sim_progress.Character import Character


class SPUpdateData:
    def __init__(self, char_obj: "Character", dynamic_buff: dict):
        """更新角色SP时的专用数据结构，仅用于传递角色的静态与动态的能量自动回复效率"""
        self.char_name = char_obj.NAME
        self.static_sp_regen: float = char_obj.statement.sp_regen
        enabled_buff: Generator = (buff for buff in dynamic_buff[self.char_name])
        self.dynamic_sp_regen: float = self.__cal_dynamic_sp_regen(enabled_buff)

    @staticmethod
    def __cal_dynamic_sp_regen(enabled_buff: Generator):
        buff_bonus: dict = cal_buff_total_bonus(enabled_buff)
        dynamic_sp_regen = buff_bonus.get("能量自动恢复", 0) + buff_bonus.get("局内能量自动恢复", 0)
        return dynamic_sp_regen

    def get_sp_regen(self) -> float:
        return self.static_sp_regen + self.dynamic_sp_regen


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
            raise TypeError("sp_value must be a number")
        if not isinstance(decibel_value, (float, int)):
            raise TypeError("decibel_value must be a number")

        self.sp_value = sp_value
        self.decibel_value = decibel_value

        # 输入验证
        if not self.sp_target or not all(isinstance(item, str) for item in self.sp_target):
            raise ValueError("sp_target must be a non-empty tuple of strings")
        if not self.decibel_target or not all(
            isinstance(item, str) for item in self.decibel_target
        ):
            raise ValueError("decibel_target must be a non-empty tuple of strings")

        allowed_kwargs = {
            "additional_param1",
            "additional_param2",
        }  # 根据实际情况定义允许的额外参数
        for key, value in kwargs.items():
            if key in allowed_kwargs:
                setattr(self, key, value)
            else:
                raise ValueError(f"Unexpected keyword argument: {key}")
