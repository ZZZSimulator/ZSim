import importlib
from .special_state_class import EnemySpecialState
from zsim.models.event_enums import SpecialStateUpdateSignal as SSUS, PostInitObjectType as PIOT
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from zsim.sim_progress.Enemy import Enemy


class SpecialStateManager:
    def __init__(self, enemy_instance: "Enemy"):
        """管理敌人特殊状态的管理器"""
        self.enemy = enemy_instance
        self.observers: dict[SSUS, list[EnemySpecialState]] = {}
        for signal in SSUS:
            self.observers[signal] = []

    def register(self, state: EnemySpecialState, signals: list[SSUS]):
        """注册对象到特定信号组"""
        for signal in signals:
            if state not in self.observers[signal]:
                self.observers[signal].append(state)
        self.enemy.sim_instance.schedule_data.change_process_state()
        print(f"【特殊状态管理器】已完成特殊状态【{state}】的注册！")

    def broadcast_and_update(self, signal: SSUS, **kwargs):
        """向所有的事件组广播事件，并执行自检和业务逻辑函数"""
        for state in self.observers[signal]:
            # if state.active:
            try:
                state.update(signal, **kwargs)
            except Exception as e:
                print(f"广播错误 ({signal.name}): {e}")

    def special_state_factory(self, state_type: PIOT, **kwargs):
        """工厂函数"""
        state_info = state_type.value
        class_name = state_info[0]
        signal_list = state_info[1]
        module = importlib.import_module('.special_classes', package=__package__)
        state_class = getattr(module, class_name)
        state_instance: EnemySpecialState = state_class(enemy_instance=self.enemy, manager_instance=self, **kwargs)
        self.register(state=state_instance, signals=signal_list)
        return state_instance





