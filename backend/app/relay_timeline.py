"""Chronological relay timeline construction from Received headers."""

from __future__ import annotations

import ipaddress
import re
from email.utils import parsedate_to_datetime

from app.schemas import ParsedEmail, RelayTimelineEvent


FROM_PATTERN = re.compile(r"\bfrom\s+([^\s(;]+)", re.IGNORECASE)
BY_PATTERN = re.compile(r"\bby\s+([^\s(;]+)", re.IGNORECASE)
IP_PATTERN = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")


def build_relay_timeline(email: ParsedEmail) -> list[RelayTimelineEvent]:
    """Turn reverse-ordered Received headers into the normal relay sequence.

    Received headers describe mail-system handling. They do not establish an
    attacker's physical route or physical location.
    """
    events: list[RelayTimelineEvent] = []
    # RFC-style Received fields are added at the top during transit, so reverse them.
    for sequence, header in enumerate(reversed(email.received_headers), start=1):
        source = _extract_host(FROM_PATTERN, header)
        destination = _extract_host(BY_PATTERN, header)
        events.append(
            RelayTimelineEvent(
                sequence=sequence,
                timestamp=_extract_timestamp(header),
                hostname=destination or source,
                ip=_extract_ipv4(header),
                source=source,
                destination=destination,
                raw_header=header,
                disclaimer="Relay-header evidence only; not an attacker's physical path.",
            )
        )
    return events


def _extract_host(pattern: re.Pattern[str], header: str) -> str | None:
    match = pattern.search(header)
    if not match:
        return None
    value = match.group(1).strip("<>[]")
    return value or None


def _extract_ipv4(header: str) -> str | None:
    for match in IP_PATTERN.finditer(header):
        candidate = match.group(0)
        try:
            if isinstance(ipaddress.ip_address(candidate), ipaddress.IPv4Address):
                return candidate
        except ValueError:
            continue
    return None


def _extract_timestamp(header: str) -> str | None:
    if ";" not in header:
        return None
    try:
        return parsedate_to_datetime(header.rsplit(";", 1)[1].strip()).isoformat()
    except (TypeError, ValueError, IndexError):
        return None
