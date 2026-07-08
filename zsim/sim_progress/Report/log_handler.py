import asyncio
import os
import queue

import aiofiles

from zsim.define import DEBUG, DEBUG_LEVEL

log_queue: queue.Queue = queue.Queue()


def report_to_log(content: str | None = None, level=4) -> None:
    if not DEBUG or content is None:
        return

    if DEBUG and DEBUG_LEVEL <= level:
        log_queue.put(content)


async def async_log_writer(result_id: str) -> None:
    report_file_path = f"./logs/{result_id}.log".replace("./results/", "")
    os.makedirs(os.path.dirname(report_file_path), exist_ok=True)
    async with aiofiles.open(report_file_path, "a", encoding="utf-8") as file:
        while True:
            lines: list[str] = []
            while True:
                try:
                    content = log_queue.get_nowait()
                except queue.Empty:
                    break
                lines.append(f"{content}\n")
            if lines:
                await file.write("".join(lines))
                await file.flush()
                for _ in lines:
                    log_queue.task_done()
                continue
            await asyncio.sleep(0.01)
