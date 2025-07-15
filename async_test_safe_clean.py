import asyncio
import signal


async def worker(name: str):
    print(f"{name} started.")
    try:
        # Simulate long-running task
        for i in range(30):
            await asyncio.sleep(10)  # total ~5 mins
            print(f"{name} running... ({(i + 1) * 10}s)")
    except asyncio.CancelledError:
        print(f"{name} was cancelled!")
        raise
    finally:
        print(f"{name} exiting.")


async def main():
    # Register tasks
    tasks = [
        asyncio.create_task(worker(name="Worker-1"), name="Worker-1"),
        asyncio.create_task(worker(name="Worker-2"), name="Worker-2"),
        asyncio.create_task(worker(name="Worker-3"), name="Worker-3"),
    ]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("Main coroutine received cancellation.")
        # Cancel all running tasks
        for task in tasks:
            if not task.done():
                task.cancel()
        # Wait for all to finish cancellation
        await asyncio.gather(*tasks, return_exceptions=True)
        print("All workers cancelled.")
        raise


def shutdown(loop, sig):
    print(f"\nReceived exit signal {sig.name}... shutting down.")
    for task in asyncio.all_tasks(loop):
        task.cancel()


if __name__ == "__main__":
    loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda sig=sig: shutdown(loop, sig))

    try:
        loop.run_until_complete(main())
    except asyncio.CancelledError:
        pass
    finally:
        print("Program terminated.")
