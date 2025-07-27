from zsim.sim_progress.Preload.APLModule.APLJudgeTools import (
    check_cid,
    find_buff,
    find_buff_0,
)
from zsim.sim_progress.Preload.APLModule.SubConditionUnit import BaseSubConditionUnit


class BuffSubUnit(BaseSubConditionUnit):
    def __init__(self, priority: int, sub_condition_dict: dict = None, mode=0):
        super().__init__(priority=priority, sub_condition_dict=sub_condition_dict, mode=mode)
        self.buff_0 = None
        self.char = None
        self.apl_warnning_dict = {}

    class BuffCheckHandler:
        @classmethod
        def handler(cls, *args, **kwargs):
            raise NotImplementedError

    class BuffExistHandler(BuffCheckHandler):
        @classmethod
        def handler(cls, game_state, char, buff_0):
            search_result = find_buff(game_state, char, buff_0.ft.index)
            if search_result is not None:
                return True
            else:
                return False

    class BuffCountHandler(BuffCheckHandler):
        @classmethod
        def handler(cls, game_state, char, buff_0):
            search_result = find_buff(game_state, char, buff_0.ft.index)
            if search_result is not None:
                return search_result.dy.count
            else:
                return 0

    class BuffDurationHandler(BuffCheckHandler):
        @classmethod
        def handler(cls, game_state, char, buff_0):
            search_result = find_buff(game_state, char, buff_0.ft.index)
            if search_result is None:
                return 0
            tick = char.sim_instance.tick
            return max(search_result.dy.endticks - tick, 0)

    BuffHandlerMap = {
        "exist": BuffExistHandler,
        "count": BuffCountHandler,
        "duration": BuffDurationHandler,
    }

    def check_myself(self, found_char_dict, game_state, *args, **kwargs):
        check_cid(self.check_target)
        if self.char is None:
            from zsim.sim_progress.Preload import find_char

            self.char = find_char(found_char_dict, game_state, int(self.check_target))
        if self.buff_0 is None:
            buff_index = self.nested_stat_key_list[0]
            search_resurt = find_buff_0(game_state, self.char, buff_index)
            if search_resurt is not None:
                self.buff_0 = search_resurt
            else:
                if self.priority not in self.apl_warnning_dict:
                    print(
                        f"【非法APL警告】优先级为{self.priority}的APL似乎与当前模拟条件不匹配！原因：在{self.char.NAME}身上并未找到名为{buff_index}的Buff！"
                    )
                    self.apl_warnning_dict[self.priority] = True
                return False
        handler_cls = self.BuffHandlerMap[self.check_stat]
        handler = handler_cls() if handler_cls else None
        if not handler:
            raise ValueError(
                f"当前检查的check_stat为：{self.check_stat}，优先级为{self.priority}，暂无处理该属性的逻辑模块！"
            )

        return self.spawn_result(handler.handler(game_state, self.char, self.buff_0))
