import asyncio
import time
from typing import Any, Callable, Optional

import aiohttp
from loguru import logger
from video_translation_client.models import (
    JobStatus,
    StatusPollingConfig,
    StatusResponse,
)


class VideoTranslationClient:
    def __init__(
        self,
        base_url: str,
        config: Optional[StatusPollingConfig] = None,
        on_status_change: Optional[Callable[[StatusResponse], Any]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.config = config or StatusPollingConfig()
        self.logger = logger
        self.on_status_change = on_status_change

    async def _get_status_once(self, session: aiohttp.ClientSession) -> StatusResponse:
        """Fetches the status of a job from the server"""
        start_time = asyncio.get_event_loop().time()
        url = f"{self.base_url}/status"

        try:
            async with session.get(url) as response:
                response.raise_for_status()

                data = await response.json()
                status = JobStatus(data["result"])
                elapsed_time = asyncio.get_event_loop().time() - start_time

                return StatusResponse(
                    status=status,
                    raw_response=data,
                    elapsed_time=elapsed_time,
                )
        except aiohttp.ClientResponseError as e:
            self.logger.error(f"HTTP error {e.status} at {url}: {e.message}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def _calculate_delay(self, attempt: int) -> float:
        """Calculates the delay for the next polling attempt using exponential backoff with an optional jitter"""
        delay = min(
            self.config.initial_delay * (self.config.backoff_factor**attempt),
            self.config.max_delay,
        )

        # Add random jitter between 0-20% of the delay
        if self.config.jitter:
            delay *= 1 + 0.2 * (asyncio.get_event_loop().time() % 1)
        return delay

    async def _handle_status_change(
        self, status_response: StatusResponse, last_status: Optional[JobStatus]
    ) -> None:
        """Invoke the status change callback if the status has changed"""
        if last_status != status_response.status and self.on_status_change is not None:
            self.logger.debug(f"Job status changed to {status_response.status}")
            await asyncio.create_task(self.on_status_change(status_response))

    async def _wait_before_retry(self, attempt: int) -> None:
        """Calculate and waits for the appropriate delay before retrying"""
        delay = self._calculate_delay(attempt)
        self.logger.debug(
            f"Job still pending, waiting {delay:.2f}s before next attempt"
        )
        await asyncio.sleep(delay)

    async def poll_until_complete(self) -> StatusResponse:
        """Poll the status endpoint until job completion or error, using exponential backoff"""
        timeout = asyncio.get_event_loop().time() + self.config.timeout
        attempt = 0
        last_status = None

        async with aiohttp.ClientSession() as session:
            while (
                asyncio.get_event_loop().time() < timeout
                and attempt < self.config.max_attempts
            ):
                try:
                    status_response = await self._get_status_once(session)

                    await self._handle_status_change(status_response, last_status)

                    last_status = status_response.status

                    if status_response.status in (JobStatus.completed, JobStatus.error):
                        return status_response

                    attempt += 1
                    await self._wait_before_retry(attempt)

                except aiohttp.ClientError as polling_error:
                    self.logger.error(f"Error polling status: {polling_error}")
                    if isinstance(polling_error, aiohttp.ClientConnectionError):
                        raise
                    await self._wait_before_retry(attempt)
                    attempt += 1

        raise TimeoutError(f"Job did not complete within {self.config.timeout} seconds")
