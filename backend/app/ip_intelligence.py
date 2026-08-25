"""Failure-safe, cached infrastructure intelligence for public IPv4 addresses."""

from __future__ import annotations

import ipaddress
import json
import socket
from functools import lru_cache
from typing import Any
from urllib.request import Request, urlopen

from app.schemas import IPIntelligence, ProbableInfrastructureLocation


LOOKUP_TIMEOUT_SECONDS = 5
PROVIDER_URL = "https://ipwho.is/{ip}"
DOCUMENTATION_NETWORKS = (
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
)
RESERVED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
)


def resolve_ip_intelligence(addresses: list[str]) -> list[IPIntelligence]:
    """Resolve IPv4 evidence explicitly observed in the analyzed email."""
    return [lookup_ip(address, source="observed_email") for address in dict.fromkeys(addresses)]


def lookup_ip(
    address: str,
    *,
    source: str = "observed_email",
    related_domains: tuple[str, ...] = (),
) -> IPIntelligence:
    """Attach evidence source metadata to a cached public-IP infrastructure lookup."""
    result = _lookup_ip_base(address)
    return result.model_copy(update={"source": source, "related_domains": list(related_domains)})


@lru_cache(maxsize=512)
def _lookup_ip_base(address: str) -> IPIntelligence:
    """Classify an address locally, then fetch public-IP infrastructure metadata when eligible."""
    address_class = classify_ipv4(address)
    if address_class != "public":
        return IPIntelligence(
            ip=address,
            address_class=address_class,
            eligible_for_lookup=False,
            lookup_available=False,
            probable_infrastructure_location=None,
        )

    try:
        payload = _fetch_provider(address)
        location = _parse_provider_payload(payload)
        if location is None:
            raise ValueError("Provider did not return usable IP intelligence.")
        return IPIntelligence(
            ip=address,
            address_class="public",
            eligible_for_lookup=True,
            lookup_available=True,
            probable_infrastructure_location=location,
        )
    except Exception:
        # External intelligence is optional. Avoid leaking provider errors to API consumers.
        return IPIntelligence(
            ip=address,
            address_class="public",
            eligible_for_lookup=True,
            lookup_available=False,
            probable_infrastructure_location=None,
        )


def classify_ipv4(address: str) -> str:
    """Return public, private, reserved, documentation, or invalid for an IPv4 string."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return "invalid"
    if not isinstance(ip, ipaddress.IPv4Address):
        return "invalid"
    if any(ip in network for network in DOCUMENTATION_NETWORKS):
        return "documentation"
    if any(ip in network for network in RESERVED_NETWORKS):
        return "reserved"
    if ip.is_private:
        return "private"
    return "public" if ip.is_global else "reserved"


def resolve_hostname(hostname: str) -> tuple[str, ...]:
    """Resolve a hostname to IPv4 infrastructure evidence, returning no data on DNS failure."""
    try:
        results = socket.getaddrinfo(hostname, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError):
        return ()
    addresses = []
    for _family, _type, _protocol, _canonical_name, sockaddr in results:
        candidate = sockaddr[0]
        if classify_ipv4(candidate) != "invalid":
            addresses.append(candidate)
    return tuple(dict.fromkeys(addresses))


def resolve_domain_intelligence(domains: list[str]) -> list[IPIntelligence]:
    """Resolve domain infrastructure only when no IP was explicitly observed in the email.

    DNS results are labeled separately and never presented as a sender or attacker IP.
    """
    ip_domains: dict[str, set[str]] = {}
    for domain in dict.fromkeys(domains):
        for address in resolve_hostname(domain):
            ip_domains.setdefault(address, set()).add(domain)
    return [
        lookup_ip(address, source="dns_resolved", related_domains=tuple(sorted(domains_for_ip)))
        for address, domains_for_ip in ip_domains.items()
    ]


def _fetch_provider(address: str) -> dict[str, Any]:
    request = Request(PROVIDER_URL.format(ip=address), headers={"Accept": "application/json"})
    with urlopen(request, timeout=LOOKUP_TIMEOUT_SECONDS) as response:  # noqa: S310 - fixed HTTPS provider URL
        return json.loads(response.read().decode("utf-8"))


def _parse_provider_payload(payload: dict[str, Any]) -> ProbableInfrastructureLocation | None:
    """Accept both current nested and legacy flat ipwho.is response shapes."""
    if payload.get("success") is False:
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    geo = data.get("geo_location") or data.get("geoLocation") or data
    connection = data.get("connection") or {}
    if not isinstance(geo, dict) or not isinstance(connection, dict):
        return None
    return ProbableInfrastructureLocation(
        country=geo.get("country"),
        region=geo.get("region") or geo.get("region_name") or geo.get("regionName"),
        city=geo.get("city"),
        latitude=geo.get("latitude"),
        longitude=geo.get("longitude"),
        isp=connection.get("isp"),
        asn=connection.get("asn") or connection.get("asn_number") or connection.get("asnNumber"),
        organization=connection.get("org") or connection.get("asn_org") or connection.get("asnOrg"),
    )


# Retain the existing cache-clear hook used by tests and local diagnostics.
lookup_ip.cache_clear = _lookup_ip_base.cache_clear
