import json
import re
import uuid
from typing import AsyncIterator

import httpx

from api.core.config import get_settings

settings = get_settings()

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_RAW_JSON_RE = re.compile(r"(\{[^{}]*\"findings\"\s*:\s*\[.*?\].*?\})", re.DOTALL)


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
        payload: dict = {"text": text, "attachments": []}
        if context_id:
            payload["context_id"] = context_id

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base}/api_message",
                json=payload,
                headers=self._headers,
            )
            response.raise_for_status()
            return response.json()

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
            '"cvss":9.8,"remediation":"..."}],"summary":"..."}'
        )
        try:
            result = await self.send_message(
                prompt, context_id=context_id, timeout=settings.json_extract_timeout
            )
            raw: str = result.get("text", "") or result.get("message", "")

            match = _JSON_BLOCK_RE.search(raw)
            if match:
                return json.loads(match.group(1))

            match = _RAW_JSON_RE.search(raw)
            if match:
                return json.loads(match.group(1))

        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            pass
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
