from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from zsim.sim_progress.data_struct import NodeStack

if TYPE_CHECKING:
    from .. import PreloadData


class BasePreloadEngine(ABC):
    @abstractmethod
    def __init__(self, data: "PreloadData"):
        self.data = data
        self.active_signal = False  # 用于记录当前引擎在当前tick是否运行过。

    @abstractmethod
    def run_myself(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    node_stack = NodeStack(3)
    a = 1
    b = 2
    c = 3
    node_stack.push(a)
    node_stack.push(b)
    node_stack.push(c)
    print(node_stack)
    d = node_stack.peek()
    e = node_stack.pop()
    print(d, e, node_stack)
