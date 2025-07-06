from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sim_progress.Character.character import Character


class HuweiManager:
    """虎威管理器，这里有虎威所有的数据机制以及业务逻辑"""
    def __init__(self, char_instance: "Character"):
        self.char = char_instance
        self.cd = 0  # 虎威的内置CD

    def check_myself(self):
        """虎威自检，内置CD啥的，若条件满足则run_myself"""
        pass

    def run_myself(self, signal: int):
        """根据传入的更新信号做出决策——到底是打平A还是打连携技或是其他"""
        # 注：通过信号来控制虎威逻辑只是一个初步设计，可能会更改。
        pass

    # 尚不确定虎威是否需要静默、被打断等逻辑，一边写一边看吧。
