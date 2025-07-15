import asyncio
from logging import Logger

from loguru import logger as base_logger


async def monitor_duration(tasks: list[asyncio.Task], timeout: int) -> None:
    log: Logger = base_logger.bind(task="monitor")
    await asyncio.sleep(timeout)
    log.warning(f"Max duration ({timeout} secs) exceeded, cancelling tasks...")
    for n, task in enumerate(tasks, start=1):
        log.warning(f"Cancelling task {n}: {task.get_name()!r}")
        task.cancel()
