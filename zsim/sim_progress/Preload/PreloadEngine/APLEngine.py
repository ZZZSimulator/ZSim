from typing import TYPE_CHECKING

from zsim.define import APL_PATH, APL_THOUGHT_CHECK
from zsim.define import APL_THOUGHT_CHECK_WINDOW as ATCW

from ..APLModule import APLManager
from ..SkillsQueue import SkillNode, spawn_node
from .BasePreloadEngine import BasePreloadEngine

if TYPE_CHECKING:
    from ..PreloadDataClass import PreloadData


class APLEngine(BasePreloadEngine):
    """用于调动APL模块的Preload引擎"""

    def __init__(self, data: "PreloadData", apl_path: str | None = None):
        super().__init__(data)
        self.preload_data = data
        self.sim_instance = self.preload_data.sim_instance
        if self.sim_instance is None:
            raise ValueError("APLEngine 初始化时必须传入 sim_instance。")
        self.apl_manager = APLManager(sim_instance=self.sim_instance)

        if apl_path is None:
            apl_path = APL_PATH
        elif not apl_path.endswith(".txt") or not apl_path.endswith(".toml"):
            # 如果提供的是APL名称而不是完整路径
            found_path = self.apl_manager.get_apl_path(apl_path)
            if found_path:
                apl_path = found_path

        self.apl = self.apl_manager.load_apl(apl_path, mode=0, preload_data=self.preload_data)
        self.latest_node: SkillNode | None = None
        self._apl_want: tuple | None = None  # APL引擎的想法

    @property
    def apl_want(self) -> tuple | None:
        return self._apl_want

    @apl_want.setter
    def apl_want(self, value: tuple | None) -> None:
        skill_tag, apl_priority, apl_unit = value if value else (None, None, None)
        if APL_THOUGHT_CHECK:
            tick = self.sim_instance.tick
            if tick in range(ATCW[0], ATCW[1]):
                if value != self.apl_want:
                    (
                        print(
                            f"{tick}tick：APL引擎的想法变化，{self.apl_want[0] if self.apl_want else None} → {skill_tag}，来自于优先级 {apl_priority} 的单元，详细内容：{apl_unit.whole_line}"
                        )
                        if self.apl_want is not None
                        else print(f"{tick}tick：APL引擎产生了第一个想法：{skill_tag}")
                    )
        self._apl_want = value

    def run_myself(self, tick) -> SkillNode | None:
        """APL模块运行的最终结果：技能名、最终通过的APL代码优先级"""
        skill_tag, apl_priority, apl_unit = self.apl.execute(tick, mode=0)
        self.apl_want = (skill_tag, apl_priority, apl_unit)
        if skill_tag == "wait":
            return None
        node = spawn_node(
            skill_tag,
            tick,
            self.data.skills,
            active_generation=True,
            apl_priority=apl_priority,
            apl_unit=apl_unit,
        )
        return node

    def reset_myself(self):
        """APL模块暂时没有任何需要Reset的地方！"""
        self.latest_node = None

    def get_available_apls(self) -> list[str]:
        """获取所有可用的APL文件列表"""
        return self.apl_manager.list_available_apls()
