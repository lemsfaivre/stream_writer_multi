import asyncio
import secrets
from typing import Any

from loguru import logger as base_logger
from settings import SourceSettings, gl_settings

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


# ======================================================================================================================
@retry(
    stop=stop_after_attempt(max_attempt_number=gl_settings.globals.max_retries),
    retry=retry_if_exception_type(exception_types=httpx.HTTPError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
async def fetch_data(client: httpx.AsyncClient, url: httpx.URL, label: int, queue: asyncio.Queue, offset_limit: int):
    log = base_logger.bind(task=label)
    api_key: str = "reqres-free-v1"
    for offset in range(offset_limit):
        page: int = offset % 2 + 1
        log.debug(f"cur={offset}/max={offset_limit}/page={page}")

        try:
            response: httpx.Response = await client.get(url=url, params={"page": page}, headers={"x-api-key": api_key})

            if response.status_code == httpx.codes.TOO_MANY_REQUESTS:
                retry_after: str = response.headers.get("Retry-After")
                delay: int = int(retry_after) if retry_after and retry_after.isdigit() else 10
                await asyncio.sleep(delay)
                raise httpx.HTTPStatusError("429 Too Many Requests", request=response.request, response=response)

            response.raise_for_status()
            data: dict[str, Any] = response.json()

            if "data" not in data and not isinstance(data.get("data"), list):
                raise ValueError(f"Expected list, but got: {type(data)}")

            log.info(f"Fetched {len(data)} records from offset: {offset}")
            for obj in data["data"]:
                obj["t0"] = True if "t0" in label else False
                await queue.put(obj)

        except httpx.HTTPError as e:
            log.error(f"HTTP error: {repr(e)}")
            raise e

        # For slow process simulation purposes
        delay: int = secrets.choice([5, 8, 11])
        log.debug(f"Sleeping {delay}")
        await asyncio.sleep(delay)


# ======================================================================================================================
async def reader_worker(api: SourceSettings, queue: asyncio.Queue, task_label: str, session: httpx.AsyncClient) -> None:
    log = base_logger.bind(task=task_label)
    log.info("Starting reader worker...")
    offset_limit: int = 2 if "t0" in task_label else 4
    try:
        await fetch_data(
            client=session, url=httpx.URL(url=str(api.url)), label=task_label, offset_limit=offset_limit, queue=queue
        )

    except asyncio.CancelledError:
        log.warning("Reader cancelled!")
    except Exception as e:
        log.exception(f"Unexpected error in reader: {repr(e)}")

    log.info("Reader finished!")
