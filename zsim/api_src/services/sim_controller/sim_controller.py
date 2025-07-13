import asyncio
from concurrent.futures import ProcessPoolExecutor

from zsim.lib_webui.multiprocess_wrapper import run_single_simulation


class SimController:
    def __init__(self):
        self._executor: ProcessPoolExecutor | None = None

    def _get_executor(self) -> ProcessPoolExecutor:
        if self._executor is None:
            self._executor = ProcessPoolExecutor()
        return self._executor

    async def run_test_simulation(self):
        """
        运行测试模拟。
        """
        loop = asyncio.get_event_loop()
        executor = self._get_executor()
        result = await loop.run_in_executor(executor, run_single_simulation, 6000)
        return result
