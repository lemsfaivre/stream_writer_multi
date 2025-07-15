#
import asyncio
import signal
import sys
from logging import Logger
from pathlib import Path
from typing import Annotated

from loguru import logger as base_logger
from rich import print
from settings import AppSettings, gl_settings

import httpx
from stream_writer_multi.controller import monitor_duration
from stream_writer_multi.reader import reader_worker
from stream_writer_multi.writer import writer_worker
from typer import Context, Exit, Option, Typer

log_format: str = (
    "<green>{time:%Y-%m-%d %H:%M:%S}</green> <level>{level:<8}</level> "
    "<cyan>{extra[task]:<14}</cyan> <level>{message}</level>"
)
base_logger.remove()
base_logger.add(
    sink=sys.stderr,
    format=log_format,
    backtrace=False,
    diagnose=False,
    level="INFO",
)

app: Typer = Typer(
    add_completion=False,
    invoke_without_command=False,
    rich_markup_mode="markdown",
    help=""" **StreamerCLI** """,
    context_settings={"help_option_names": ["-h", "--help"]},
)


# ======================================================================================================================
@app.callback(invoke_without_command=True)
def callback(ctx: Context):
    if ctx.invoked_subcommand is None and not ctx.args:
        ctx.invoke(run)


# ======================================================================================================================
@app.command(name="settings", help="display settings")
def display_settings(
    settings_path: Annotated[Path, Option("-s", "--settings", help="Settings file path")] = Path("./settings.toml"),
) -> None:
    log: Logger = base_logger.bind(task="main")
    try:
        settings: AppSettings = AppSettings.from_toml(path=settings_path)
        print(settings)
    except Exception as e:
        log.error(f"Cannot read settings file: {settings_path}!")
        log.error(f"{repr(e)}")
        raise Exit()


# ======================================================================================================================
@app.command(name="run", help="run the tool")
def run(
    settings_path: Annotated[Path, Option("--settings", "-s", help="Settings file path")] = Path("./settings.toml"),
) -> None:
    asyncio.run(main=main(settings_path=settings_path))


# ======================================================================================================================
async def main(settings_path: Path) -> None:
    log: Logger = base_logger.bind(task="main")
    print(gl_settings)
    try:
        settings: AppSettings = AppSettings.from_toml(path=settings_path)
    except Exception as e:
        log.error(f"Cannot read settings file: {settings_path}!")
        log.error(f"{repr(e)}")
        raise Exit()

    asyncio.current_task().set_name("main")

    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda sig=sig: shutdown(loop))

    queue_1: asyncio.Queue = asyncio.Queue(maxsize=settings.globals.queue_maxsize)
    queue_2: asyncio.Queue = asyncio.Queue(maxsize=settings.globals.queue_maxsize)

    output_queues: dict[int, asyncio.Queue] = {1: queue_1, 2: queue_2}

    limits: httpx.Limits = httpx.Limits(max_connections=10, max_keepalive_connections=8)
    async with httpx.AsyncClient(timeout=30, limits=limits) as session:
        reader_tasks: list[asyncio.Task] = list()
        for name, source in settings.sources.items():
            queue: asyncio.Queue = output_queues.get(source.output_stream)
            if not queue:
                raise ValueError(f"Invalid output stream {source.output_stream} for source {name}")

            reader_tasks.append(
                asyncio.create_task(reader_worker(queue=queue, task_label=name, api=source, session=session), name=name)
            )

        writer_tasks: list[asyncio.Task] = list()
        for name, output in settings.outputs.items():
            queue: asyncio.Queue = output_queues.get(output.stream)
            writer_tasks.append(
                asyncio.create_task(writer_worker(queue=queue, task_label=name, config=output), name=name)
            )

        # Start timout monitor
        all_tasks: list[asyncio.Task] = reader_tasks + writer_tasks
        asyncio.create_task(
            monitor_duration(tasks=all_tasks, timeout=settings.globals.max_duration_secs), name="monitor"
        )

        try:
            await asyncio.gather(*reader_tasks)
            await queue_1.put(None)
            await queue_2.put(None)
            await asyncio.gather(*writer_tasks)
        except asyncio.CancelledError:
            log.warning("Program manually terminated!")
        except Exception as e:
            log.error(f"Unknown exception: {repr(e)}!")


# ======================================================================================================================
# async def shutdown(loop: asyncio.AbstractEventLoop):
def shutdown(loop: asyncio.AbstractEventLoop):
    log: Logger = base_logger.bind(task="shutdown")
    tasks: list[asyncio.Task] = [t for t in asyncio.all_tasks(loop) if not t.done() and t.get_name() not in ["main"]]
    for n, task in enumerate(tasks, start=1):
        log.warning(f"Cancelling task {n}: {task.get_name()}...")
        task.cancel()


if __name__ == "__main__":
    app()
