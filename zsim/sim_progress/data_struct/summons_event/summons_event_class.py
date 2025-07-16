from abc import ABC, abstractmethod
from zsim.sim_progress.summons.summons_class import Summons
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator


class SummonsEvent(ABC):
    @abstractmethod
    def __init__(self, summons_obj: Summons,  execute_tick: int, event: object | None = None):
        self.summons = summons_obj
        self.description: str | None = None
        self.event = event
        self.execute_tick: int = execute_tick
        self._has_executed: bool = False
        self._change_state: bool = False        # 状态锁定标志

    @property
    def has_executed(self):
        """是否被处理过"""
        return self._has_executed

    @has_executed.setter
    def has_executed(self, value: bool):
        if self._change_state:
            raise RuntimeError("执行状态不允许被反复修改！")
        self._has_executed = value
        self._change_state = True

    def execute_myself(self):
        """业务逻辑接口"""
        self._execute_myself()
        self._post_execute_check()

    def _post_execute_check(self):
        """后置检查"""
        if not self.has_executed:
            sim_instance: "Simulator" = self.summons.sim_instance
            sim_instance.schedule_data.change_process_state()
            print("【SummonsEvent警告】：在运行业务逻辑后，自身执行状态未被更改，请检查代码！")

    @abstractmethod
    def _execute_myself(self):
        """实际业务逻辑"""
        pass

