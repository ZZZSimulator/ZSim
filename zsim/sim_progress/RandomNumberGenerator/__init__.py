import random
import threading
import time
from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from zsim.simulator.simulator_class import Simulator

MAX_SIGNED_INT64: int = 2**63 - 1


class RNG:
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, sim_instance: "Simulator"):
        """为了RNG增加进程锁"""
        with cls._lock:
            if sim_instance not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[sim_instance] = instance
            return cls._instances[sim_instance]

    def __init__(self, sim_instance: "Simulator" = None):
        """RNG的构造函数，每个进程只执行一次，反复调用构造函数会报错。"""
        if not hasattr(self, "_initialized"):
            self.seed: int | None = None
            self.r: int | None = None
            self.sim_instance = sim_instance
            self.reseed()
            self._initialized = True
            self.NORMAL_TABLE_SIZE = 10000
            self.normal_table = None
        else:
            raise RuntimeError("RNG对象已初始化，请检查代码，不要重复调用RNG的构造函数")

    def get_seed(self) -> int:
        assert self.seed is not None
        return self.seed

    def reseed(self, new_seed: int | None = None):
        if self.sim_instance is None:
            raise ValueError("RNG模块在初始化时，并未传入Simulator对象")

        if self.sim_instance.in_parallel_mode:
            """当多进程模式时，seed的创造应该基于进程的UUID"""
            run_turn_uuid: str = self.sim_instance.sim_cfg.run_turn_uuid
            if run_turn_uuid is None:
                raise ValueError("多进程模式下，sim_cfg中必须存在有效的run_turn_uuid")
            hashed_uuid = abs(hash(run_turn_uuid)) % (2**63)
            tick = self.sim_instance.tick
            new_seed = (hashed_uuid + tick) if new_seed is None else (new_seed + tick)
        else:
            """当单进程模式时，seed的创造应该基于当前的time()返回的结果"""
            tick = self.sim_instance.tick
            if new_seed is None:
                new_seed = int(time.time() * 1000000) + tick
            else:
                new_seed = int(new_seed) + tick
        (self.seed, self.r) = self.generate_random_number(new_seed)
        random.seed(self.seed)

    def random_float(self) -> float:
        return random.uniform(0.0, 1.0)

    @staticmethod
    @lru_cache(maxsize=4)
    def generate_random_number(seed: int) -> tuple[int, int]:
        random.seed(seed)
        random_number = random.randint(a=-MAX_SIGNED_INT64, b=MAX_SIGNED_INT64)
        return seed, random_number

    def generate_and_judge(self, possibility: float) -> bool:
        self.seed, self.r = self.generate_random_number(self.seed)
        return np.abs(self.r) < possibility * MAX_SIGNED_INT64

    def normal_from_table(self) -> float:
        """生成正态分布的随机数，使用预先生成的正态分布表"""

        if not hasattr(self, "normal_table") or self.normal_table is None:
            self.normal_table = np.random.normal(
                loc=0, scale=1, size=self.NORMAL_TABLE_SIZE
            )
        rng_float = self.random_float()
        idx = int(rng_float * self.NORMAL_TABLE_SIZE)
        idx = min(idx, self.NORMAL_TABLE_SIZE - 1)
        value = self.normal_table[idx]
        return float(value)

    def __deepcopy__(self, memo):
        return self  # 始终返回现有实例

    def __copy__(self):
        return self
