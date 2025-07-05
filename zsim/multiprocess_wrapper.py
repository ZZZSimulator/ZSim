"""多进程包装器模块

用于解决函数序列化问题的包装器
"""

from typing import Any
import io
from contextlib import redirect_stdout
from zsim.simulator import Simulator


def run_single_simulation(stop_tick: int) -> str:
    """运行单次模拟的包装函数
    
    这个函数在模块级别定义，可以被pickle序列化
    
    Args:
        stop_tick: 模拟停止的tick数
        
    Returns:
        模拟结果字符串
    """
    try:
        f = io.StringIO()
        with redirect_stdout(f):
            print("启动子进程")
            sim_ins = Simulator()
            sim_ins.main_loop(stop_tick)
        return f.getvalue()
    except Exception as e:
        return f"错误：启动子进程失败 - {str(e)}"


def run_subprocess_simulation(stop_tick: int) -> str:
    """运行子进程模拟的包装函数
    
    Args:
        stop_tick: 模拟停止的tick数
        
    Returns:
        模拟结果字符串
    """
    import subprocess
    import sys
    
    try:
        results = []
        command = [sys.executable, "zsim/main.py", "--stop-tick", str(stop_tick)]
        proc = subprocess.run(command, capture_output=True, text=True)
        results.append(proc.stdout.strip())
        return "\n".join(results)
    except Exception as e:
        return f"错误：启动子进程失败 - {str(e)}"