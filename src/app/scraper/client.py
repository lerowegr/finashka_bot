import asyncio
import logging
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

log = logging.getLogger(__name__)


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500


class SiteClient:
    """Единственная точка обращений к tabiturient.ru: вежливый rate-limit + ретраи."""

    def __init__(self, rps: float | None = None):
        self._min_interval = 1.0 / (rps or settings.scrape_rps)
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._client = httpx.AsyncClient(
            base_url=settings.source_base_url,
            headers={"User-Agent": settings.user_agent},
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
            http2=True,
        )

    async def _throttle(self) -> None:
        async with self._lock:
            wait = self._last_request + self._min_interval - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()

    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=2, max=60),
        reraise=True,
    )
    async def get(self, path: str) -> str:
        await self._throttle()
        response = await self._client.get(path)
        response.raise_for_status()
        return response.text

    async def close(self) -> None:
        await self._client.aclose()
