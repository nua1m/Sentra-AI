import json
import re
import uuid

import httpx

from api.core.config import get_settings

settings = get_settings()

_JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_RAW_JSON_RE = re.compile(r"(\{[^{}]*\"findings\"\s*:\s*\[.*?\].*?\})", re.DOTALL)


class Agent0Client:
    """Thin async HTTP client for Agent0's REST API.

    Uses one httpx.AsyncClient per instance — callers should reuse the same
    instance (injected via FastAPI dependency) rather than creating many.
    """

    def __init__(self) -> None:
        self._base = settings.agent0_internal_url.rstrip("/")
        self._headers = {"X-API-Key": settings.agent0_api_key}

    async def _post_message(
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

    async def run_scan(self, target: str, scan_type: str = "full") -> dict:
        """Call 1 — send the scan request and get back the full report."""
        prompt = (
            f"Run a {'full security audit' if scan_type == 'full' else scan_type + ' scan'} "
            f"on {target}. Provide the complete findings report."
        )
        return await self._post_message(prompt, timeout=settings.scan_timeout_seconds)

    async def extract_json(self, context_id: str) -> dict | None:
        """Call 2 — ask Agent0 to reformat previous findings as structured JSON."""
        prompt = (
            "Based on your previous security findings report, output ONLY a valid JSON object "
            "using this exact schema — no markdown, no explanation, JSON only:\n"
            '{"target":"...","scan_date":"ISO date","tools_used":["nmap"],'
            '"findings":[{"severity":"critical|high|medium|low|info",'
            '"title":"...","tool":"...","cve":"CVE-XXXX or null",'
            '"cvss":9.8,"remediation":"..."}],"summary":"..."}'
        )
        try:
            result = await self._post_message(
                prompt,
                context_id=context_id,
                timeout=settings.json_extract_timeout,
            )
            raw_text: str = result.get("text", "") or result.get("message", "")

            # Try fenced code block first
            match = _JSON_BLOCK_RE.search(raw_text)
            if match:
                return json.loads(match.group(1))

            # Try bare JSON object
            match = _RAW_JSON_RE.search(raw_text)
            if match:
                return json.loads(match.group(1))

        except (httpx.HTTPError, json.JSONDecodeError, KeyError):
            pass

        return None

    async def check_health(self) -> bool:
        """Ping Agent0 to verify connectivity."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self._base}/", headers=self._headers)
                return r.status_code < 500
        except httpx.HTTPError:
            return False


def get_agent0_client() -> Agent0Client:
    """FastAPI dependency — returns a shared client instance."""
    return Agent0Client()
