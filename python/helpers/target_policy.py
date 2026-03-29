from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse


AUTHORIZED_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "host.docker.internal",
    "dvwa",
    "juice-shop",
    "sentra-demo-vulnerable",
    "sentra-demo-remediated",
}

AUTHORIZED_SUFFIXES = (".local", ".internal")


def _extract_host(value: str) -> str:
    candidate = value.strip().strip("'\"")
    if "://" in candidate:
        parsed = urlparse(candidate)
        return (parsed.hostname or "").strip().lower()
    if "/" in candidate:
        candidate = candidate.split("/", 1)[0]
    if candidate.count(":") == 1 and not candidate.startswith("["):
        host, maybe_port = candidate.rsplit(":", 1)
        if maybe_port.isdigit():
            candidate = host
    return candidate.strip().lower()


def is_authorized_target(value: str) -> tuple[bool, str]:
    host = _extract_host(value)
    if not host:
        return False, "No valid target host was found."

    if host in AUTHORIZED_HOSTS:
        return True, host

    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback or ip.is_private:
            return True, host
        return (
            False,
            f"Public IP target '{host}' is outside Sentra's authorized local-lab scope.",
        )
    except ValueError:
        pass

    if host.endswith(AUTHORIZED_SUFFIXES):
        return True, host

    return (
        False,
        f"Public-domain target '{host}' is outside Sentra's authorized local-lab scope.",
    )


_URL_RE = re.compile(r"https?://[^\s\"']+")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HOST_RE = re.compile(r"\b[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}\b")


def extract_candidate_targets(text: str) -> list[str]:
    candidates: list[str] = []
    for match in _URL_RE.findall(text):
        candidates.append(match)
    for match in _IP_RE.findall(text):
        candidates.append(match)
    for match in _HOST_RE.findall(text):
        candidates.append(match)
    return list(dict.fromkeys(candidates))


def validate_targets(values: list[str]) -> tuple[bool, str | None]:
    for value in values:
        ok, reason = is_authorized_target(value)
        if not ok:
            return False, reason
    return True, None
