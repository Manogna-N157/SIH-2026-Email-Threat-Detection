import json

from app import ip_intelligence


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_non_public_ranges_are_never_sent_to_provider(monkeypatch) -> None:
    ip_intelligence.lookup_ip.cache_clear()
    calls = []
    monkeypatch.setattr(ip_intelligence, "urlopen", lambda *_args, **_kwargs: calls.append(True))

    results = ip_intelligence.resolve_ip_intelligence(
        ["10.0.0.1", "192.0.2.10", "127.0.0.1", "198.51.100.5"]
    )

    assert [result.address_class for result in results] == ["private", "documentation", "reserved", "documentation"]
    assert all(not result.eligible_for_lookup for result in results)
    assert calls == []


def test_public_ip_returns_probable_infrastructure_location_and_is_cached(monkeypatch) -> None:
    ip_intelligence.lookup_ip.cache_clear()
    calls = []
    payload = {
        "success": True,
        "country": "United States",
        "region": "California",
        "city": "Mountain View",
        "latitude": 37.4,
        "longitude": -122.1,
        "connection": {"asn": 15169, "isp": "Google LLC", "org": "Google LLC"},
    }

    def fake_urlopen(*_args, **_kwargs):
        calls.append(True)
        return FakeResponse(payload)

    monkeypatch.setattr(ip_intelligence, "urlopen", fake_urlopen)

    first = ip_intelligence.lookup_ip("8.8.8.8")
    second = ip_intelligence.lookup_ip("8.8.8.8")

    assert first == second
    assert len(calls) == 1
    assert first.lookup_available is True
    assert first.probable_infrastructure_location is not None
    assert first.probable_infrastructure_location.city == "Mountain View"
    assert first.probable_infrastructure_location.region == "California"
    assert first.probable_infrastructure_location.asn == 15169
    assert first.source == "observed_email"


def test_provider_failure_preserves_pipeline_safe_result(monkeypatch) -> None:
    ip_intelligence.lookup_ip.cache_clear()

    def failing_urlopen(*_args, **_kwargs):
        raise TimeoutError()

    monkeypatch.setattr(ip_intelligence, "urlopen", failing_urlopen)

    result = ip_intelligence.lookup_ip("1.1.1.1")

    assert result.address_class == "public"
    assert result.eligible_for_lookup is True
    assert result.lookup_available is False
    assert result.probable_infrastructure_location is None


def test_dns_resolved_infrastructure_is_labeled_separately(monkeypatch) -> None:
    ip_intelligence.lookup_ip.cache_clear()
    monkeypatch.setattr(
        ip_intelligence.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("8.8.4.4", 0))],
    )
    monkeypatch.setattr(
        ip_intelligence,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            {"success": True, "country": "United States", "connection": {"asn": 15169, "isp": "Google LLC", "org": "Google LLC"}}
        ),
    )

    results = ip_intelligence.resolve_domain_intelligence(["portal.example.test"])

    assert len(results) == 1
    assert results[0].ip == "8.8.4.4"
    assert results[0].source == "dns_resolved"
    assert results[0].related_domains == ["portal.example.test"]


def test_dns_failure_returns_no_invented_infrastructure(monkeypatch) -> None:
    monkeypatch.setattr(ip_intelligence.socket, "getaddrinfo", lambda *_args, **_kwargs: (_ for _ in ()).throw(ip_intelligence.socket.gaierror()))

    assert ip_intelligence.resolve_domain_intelligence(["does-not-resolve.example.test"]) == []
