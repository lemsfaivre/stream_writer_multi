import asyncio
import json
from logging import Logger

import aiofiles
from loguru import logger as base_logger
from settings import OutputSettings


# async def writer_worker(task_label: str, queue: asyncio.Queue, output_file: str):
async def writer_worker(task_label: str, queue: asyncio.Queue, config: OutputSettings):
    log: Logger = base_logger.bind(task=task_label)
    log.info("Starting writer worker...")
    try:
        async with aiofiles.open(config.filename, "w") as f:
            while True:
                item = await queue.get()
                if item is None:
                    break
                try:
                    line: str = json.dumps(item)
                    await f.write(line + "\n")
                except Exception as e:
                    log.error(f"Failed to write record: {repr(e)}")
    except asyncio.CancelledError:
        log.warning("Writer cancelled!")
    log.info("Writer finished!")
