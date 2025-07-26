from typing import TYPE_CHECKING

from .BaseSubConditionUnit import BaseSubConditionUnit

if TYPE_CHECKING:
    from ...PreloadDataClass import PreloadData


class SpecialSubUnit(BaseSubConditionUnit):
    def __init__(self, priority: int, sub_condition_dict: dict = None, mode=0):
        super().__init__(priority=priority, sub_condition_dict=sub_condition_dict, mode=mode)
        self.preload_data = None

    class SpecialHandler:
        @classmethod
        def handler(cls, *args, **kwargs):
            raise NotImplementedError

    class OperatingCharacterHandler(SpecialHandler):
        @classmethod
        def handler(cls, preload_data):
            cid = preload_data.operating_now
            # print(f'调用了特殊检查，当前正在操作的CID为：{cid}')
            return cid

    class IsAttackingHandler(SpecialHandler):
        @classmethod
        def handler(cls, preload_data: "PreloadData"):
            atk_manager = preload_data.atk_manager
            if atk_manager is None:
                return False
            return atk_manager.attacking

    SpecialHandlerMap = {
        "operating_char": OperatingCharacterHandler,
        "is_attacking": IsAttackingHandler,
    }

    def check_myself(self, found_char_dict, game_state, *args, **kwargs):
        if self.preload_data is None:
            preload = game_state.get("preload", None)
            if preload is None:
                raise ValueError(
                    "为从gamestate中获取到preload数据，请检查game_state的preload数据是否正常！"
                )
            self.preload_data = preload.preload_data
        handler_cls = self.SpecialHandlerMap.get(self.check_stat)
        handler = handler_cls() if handler_cls else None
        if not handler:
            raise ValueError(
                f"当前检查的check_stat为：{self.check_stat}，优先级为{self.priority}，暂无处理该属性的逻辑模块！"
            )
        __result = self.spawn_result(handler.handler(self.preload_data))
        # if __result and self.priority == 6:
        #     print(handler.handler(self.preload_data)), print(self.preload_data.latest_active_generation_node.skill_tag)
        return __result
