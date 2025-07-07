from ...APLModule.APLJudgeTools import check_cid, get_nested_value
from ...APLModule.SubConditionUnit import BaseSubConditionUnit


class AttributeSubUnit(BaseSubConditionUnit):
    def __init__(self, priority: int, sub_condition_dict: dict = None, mode=0):
        super().__init__(
            priority=priority, sub_condition_dict=sub_condition_dict, mode=mode
        )
        self.char = None

    class AttributeCheckHandler:
        @classmethod
        def handler(cls, *args, **kwargs):
            raise NotImplementedError

    class EnergyHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, **kwargs):
            return char.sp

    class DecibelHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, **kwargs):
            return char.decibel

    class SpecialResourceValueHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, **kwargs):
            return char.get_resources()[1]

    class SpecialResourceTypeHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, **kwargs):
            return char.get_resources()[0]

    class SpecialStateHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, nested_stat_key_list: list = None, **kwargs):
            if nested_stat_key_list:
                return get_nested_value(nested_stat_key_list, char.get_special_stats())
            else:
                return char.get_special_stats()

    class CinemaHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, **kwargs):
            return char.cinema

    class AdrenalineHandler(AttributeCheckHandler):
        @classmethod
        def handler(cls, char, **kwargs):
            if not hasattr(char, "adrenaline"):
                raise AttributeError(f"尝试在角色{char.NAME}中访问闪能！")
            return char.adrenaline

    AttributeHandlerMap = {
        "energy": EnergyHandler,
        "decibel": DecibelHandler,
        "special_resource": SpecialResourceValueHandler,
        "special_resource_type": SpecialResourceTypeHandler,
        "special_state": SpecialStateHandler,
        "cinema": CinemaHandler,
        "adrenaline": AdrenalineHandler,
    }

    def check_myself(self, found_char_dict, game_state: dict, *args, **kwargs):
        """处理 属性判定类 的子条件"""
        tick = kwargs.get("tick", None)
        check_cid(self.check_target)
        if self.char is None:
            from zsim.sim_progress.Preload import find_char

            self.char = find_char(found_char_dict, game_state, int(self.check_target))
        handler_cls = self.AttributeHandlerMap.get(self.check_stat)
        handler = handler_cls() if handler_cls else None
        if not handler:
            raise ValueError(
                f"当前检查的check_stat为：{self.check_stat}，优先级为{self.priority}，暂无处理该属性的逻辑模块！"
            )
        if self.check_stat != "special_state":
            return self.spawn_result(handler.handler(self.char, tick=tick))
        else:
            return self.spawn_result(
                handler.handler(self.char, self.nested_stat_key_list, tick=tick)
            )
