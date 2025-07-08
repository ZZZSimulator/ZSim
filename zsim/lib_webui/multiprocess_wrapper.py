import io
from contextlib import redirect_stdout
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zsim.simulator.config_classes import (
        SimulationConfig as SimCfg,
    )


def run_single_simulation(stop_tick: int) -> str:
    """运行单次模拟的包装函数

    这个函数在模块级别定义，可以被pickle序列化

    Args:
        stop_tick: 模拟停止的tick数

    Returns:
        模拟结果字符串
    """
    from zsim.simulator import Simulator  # 真正启动模拟再导入，以优化启动速度

    f = io.StringIO()
    with redirect_stdout(f):
        print("启动子进程")
        sim_ins = Simulator()
        sim_ins.main_loop(stop_tick)
    return f.getvalue()


def run_parallel_simulation(sim_cfg: "SimCfg") -> str:
    """运行并行模拟的包装函数

    这个函数在模块级别定义，可以被pickle序列化

    Args:
        stop_tick: 模拟停止的tick数
        sim_cfg: 模拟配置

    Returns:
        模拟结果字符串
    """
    from zsim.simulator import Simulator  # 真正启动模拟再导入，以优化启动速度

    f = io.StringIO()
    with redirect_stdout(f):
        print("启动子进程")
        sim_ins = Simulator()
        sim_ins.main_loop(stop_tick=sim_cfg.stop_tick, sim_cfg=sim_cfg)
    return f.getvalue()
