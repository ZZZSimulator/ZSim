import os
from typing import TYPE_CHECKING, Optional

from zsim.define import COSTOM_APL_DIR, DEFAULT_APL_DIR

from .APLClass import APLClass
from .APLParser import APLParser

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator

    from .. import PreloadData


class APLManager:
    """APL管理器，用于管理和加载APL代码文件"""

    def __init__(self, sim_instance: "Simulator" = None):
        self.default_apl_dir = DEFAULT_APL_DIR
        self.custom_apl_dir = COSTOM_APL_DIR
        self._ensure_directories()
        self.sim_instance = sim_instance

    def _ensure_directories(self):
        """确保必要的目录存在"""
        os.makedirs(self.default_apl_dir, exist_ok=True)
        os.makedirs(self.custom_apl_dir, exist_ok=True)

    def get_apl_path(self, name: str) -> Optional[str]:
        """
        获取APL文件的完整路径
        :param name: APL文件名（可以带或不带.txt后缀）
        :return: 完整的文件路径，如果文件不存在则返回None
        """
        if not name.endswith(".txt"):
            name = f"{name}.txt"

        # 按照优先级依次查找
        search_paths = [
            os.path.join(self.custom_apl_dir, name),
            os.path.join(self.default_apl_dir, name),
        ]

        for path in search_paths:
            if os.path.exists(path):
                return path
        return None

    def load_apl(
        self, path: str, mode: int = 0, preload_data: "PreloadData" = None
    ) -> APLClass:
        """
        加载并解析APL文件
        :param path: APL文件路径
        :param mode: 解析模式（0为普通模式，1为默认配置模式）
        :param preload_data: 外部传入的Preload_data
        :return: 已初始化的APLClass实例
        """
        return APLClass(
            APLParser(file_path=path).parse(mode=mode),
            preload_data=preload_data,
            sim_instance=self.sim_instance,
        )

    def list_available_apls(self) -> list[str]:
        """
        列出所有可用的APL文件
        :return: APL文件名列表
        """
        apls = []
        for directory in [self.default_apl_dir, self.custom_apl_dir]:
            if os.path.exists(directory):
                apls.extend([f for f in os.listdir(directory) if f.endswith(".txt")])
        return list(set(apls))  # 去重
