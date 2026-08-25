from pathlib import Path

from app.email_parser import parse_eml
from app.relay_timeline import build_relay_timeline


DATASET_DIR = Path(__file__).resolve().parents[2] / "dataset"


def test_received_headers_become_chronological_relay_timeline() -> None:
    email = parse_eml((DATASET_DIR / "EMAIL-001.eml").read_bytes())

    timeline = build_relay_timeline(email)

    assert len(timeline) == 2
    assert [event.sequence for event in timeline] == [1, 2]
    assert timeline[0].source == "origin.example.com"
    assert timeline[0].destination == "outbound.example.com"
    assert timeline[0].ip == "198.51.100.20"
    assert timeline[0].timestamp == "2026-08-24T08:00:00+00:00"
    assert timeline[1].source == "outbound.example.com"
    assert timeline[1].destination == "mx.example.com"
    assert timeline[1].ip == "203.0.113.20"
    assert "not an attacker's physical path" in timeline[0].disclaimer


def test_malformed_received_header_still_creates_safe_event() -> None:
    email = parse_eml(
        b"""From: sender@example.com
Received: malformed relay data
Content-Type: text/plain

Hello"""
    )

    timeline = build_relay_timeline(email)

    assert len(timeline) == 1
    assert timeline[0].timestamp is None
    assert timeline[0].source is None
    assert timeline[0].destination is None
