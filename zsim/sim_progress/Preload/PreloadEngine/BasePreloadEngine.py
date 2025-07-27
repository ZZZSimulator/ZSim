from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .. import PreloadData


class BasePreloadEngine(ABC):
    @abstractmethod
    def __init__(self, data: "PreloadData"):
        self.data = data
        self.active_signal = False  # 用于记录当前引擎在当前tick是否运行过。

    @abstractmethod
    def run_myself(self, *args, **kwargs) -> Any:
        return False


__all__ = ["BasePreloadEngine"]
