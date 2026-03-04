import asyncio
import json
import logging
import re
import time
import uuid
from typing import AsyncIterator

import httpx

from api.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_RAW_JSON_RE = re.compile(r"(\{[^{}]*\"findings\"\s*:\s*\[.*?\].*?\})", re.DOTALL)
_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


class Agent0Client:
    """Async HTTP client for Agent0's REST API."""

    def __init__(self) -> None:
        self._base = settings.agent0_internal_url.rstrip("/")
        self._headers = {"X-API-Key": settings.agent0_api_key}

    async def send_message(
        self,
        text: str,
        context_id: str | None = None,
        timeout: int = settings.scan_timeout_seconds,
    ) -> dict:
        payload: dict = {"message": text, "attachments": []}
        if context_id:
            payload["context_id"] = context_id

        def _send() -> dict:
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    with httpx.Client(timeout=timeout) as client:
                        response = client.post(
                            f"{self._base}/api_message",
                            json=payload,
                            headers={**self._headers, "Connection": "close"},
                        )
                        response.raise_for_status()
                        data = response.json()
                        if "response" in data and "message" not in data:
                            data["message"] = data["response"]
                        return data
                except httpx.HTTPError as exc:
                    transient = exc.__class__.__name__ in {
                        "RemoteProtocolError",
                        "ConnectError",
                        "ReadTimeout",
                    }
                    if not transient:
                        cause = getattr(exc, "__cause__", None)
                        logger.error(
                            "Agent0 /api_message request failed: %s",
                            exc,
                            exc_info=True,
                        )
                        print(
                            f"Agent0 /api_message request failed: {exc!r}; cause={cause!r}"
                        )
                        raise

                    if attempt >= max_attempts:
                        cause = getattr(exc, "__cause__", None)
                        logger.error(
                            "Agent0 /api_message request failed after retries: %s",
                            exc,
                            exc_info=True,
                        )
                        print(
                            f"Agent0 /api_message request failed: {exc!r}; cause={cause!r}"
                        )
                        raise
                    time.sleep(1.0 * attempt)

            raise RuntimeError("Agent0 request retry loop exited unexpectedly")

        return await asyncio.to_thread(_send)

    async def get_log(self, context_id: str, start: int = 0) -> dict:
        """Fetch log items from Agent0 for a given context_id starting at offset."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._base}/api_log_get",
                    params={"context_id": context_id, "start": start},
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return {"items": []}

    async def stream_log(
        self, context_id: str, poll_interval: float = 1.0
    ) -> AsyncIterator[str]:
        """Async generator that yields new log lines as they appear."""
        import asyncio

        seen = 0
        while True:
            data = await self.get_log(context_id, start=seen)
            items = data.get("items", [])
            for item in items:
                # Each item may have 'content' or 'text' field
                line = item.get("content") or item.get("text") or str(item)
                if line:
                    yield line
            seen += len(items)
            await asyncio.sleep(poll_interval)

    async def extract_json(self, context_id: str) -> dict | None:
        """Second call — ask Agent0 to reformat previous findings as pure JSON."""
        prompt = (
            "Based on your previous security findings report, output ONLY a valid JSON object "
            "using this exact schema — no markdown, no explanation, JSON only:\n"
            '{"target":"...","scan_date":"ISO date","tools_used":["nmap"],'
            '"findings":[{"severity":"critical|high|medium|low|info",'
            '"title":"...","tool":"...","cve":"CVE-XXXX or null",'
            '"cvss":9.8,"remediation":"..."}],"summary":"..."}\n'
            f"request_id: {uuid.uuid4()}"
        )
        try:
            result = await self.send_message(
                prompt, context_id=context_id, timeout=settings.json_extract_timeout
            )
            raw: str = (
                result.get("text", "")
                or result.get("message", "")
                or result.get("response", "")
            )
            return self.parse_scan_json(raw)

        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            pass
        return None

    def parse_scan_json(self, raw: str) -> dict | None:
        cleaned = _ANSI_ESCAPE_RE.sub("", raw).strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "findings" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        match = _JSON_BLOCK_RE.search(cleaned)
        if match:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and "findings" in parsed:
                return parsed

        match = _RAW_JSON_RE.search(cleaned)
        if match:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and "findings" in parsed:
                return parsed

        first = cleaned.find("{")
        last = cleaned.rfind("}")
        if first != -1 and last != -1 and first < last:
            parsed = json.loads(cleaned[first : last + 1])
            if isinstance(parsed, dict) and "findings" in parsed:
                return parsed

        return None

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base}/", headers=self._headers)
                return r.status_code < 500
        except httpx.HTTPError:
            return False


def get_agent0_client() -> Agent0Client:
    return Agent0Client()
