"""Frontend-independent evidence graph generation for email analysis."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit

from app.schemas import GraphEdge, GraphNode, IPIntelligence, ParsedEmail, ThreatGraph


FQDN_PATTERN = re.compile(r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}\b")


def build_threat_graph(email: ParsedEmail, ip_intelligence: list[IPIntelligence]) -> ThreatGraph:
    """Build stable, visualizer-agnostic graph data from observed email evidence."""
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    email_id = _email_id(email)
    _add_node(
        nodes, email_id, "EMAIL", email.subject or "Email message",
        {"message_id": email.message_id, "subject": email.subject, "date": email.date},
    )

    for sender in email.from_:
        if sender.address:
            sender_id = _id("sender", sender.address.lower())
            _add_node(nodes, sender_id, "SENDER", sender.address, sender.model_dump())
            _add_edge(edges, email_id, sender_id, "sent_by")

    for reply_to in email.reply_to:
        if reply_to.address:
            reply_id = _id("reply-to", reply_to.address.lower())
            _add_node(nodes, reply_id, "REPLY_TO", reply_to.address, reply_to.model_dump())
            _add_edge(edges, email_id, reply_id, "replies_to")

    domains = set(email.domains)
    domains.update(domain for record in ip_intelligence for domain in record.related_domains)
    received_domain_to_ips: dict[str, set[str]] = {}
    for header in email.received_headers:
        header_domains = {domain.lower() for domain in FQDN_PATTERN.findall(header)}
        header_ips = {ip for ip in email.ipv4_addresses if ip in header}
        domains.update(header_domains)
        for domain in header_domains:
            received_domain_to_ips.setdefault(domain, set()).update(header_ips)

    domain_ids: dict[str, str] = {}
    for domain in sorted(domains):
        domain_id = _id("domain", domain.lower())
        domain_ids[domain.lower()] = domain_id
        _add_node(nodes, domain_id, "DOMAIN", domain, {"domain": domain})
        _add_edge(edges, email_id, domain_id, "references_domain")

    for url in email.urls:
        url_id = _id("url", url)
        _add_node(nodes, url_id, "URL", url, {"url": url})
        _add_edge(edges, email_id, url_id, "contains_url")
        hostname = urlsplit(url if "://" in url else f"http://{url}").hostname
        if hostname and hostname.lower() in domain_ids:
            _add_edge(edges, url_id, domain_ids[hostname.lower()], "hosted_on")

    intelligence_by_ip = {record.ip: record for record in ip_intelligence}
    all_ips = list(dict.fromkeys([*email.ipv4_addresses, *intelligence_by_ip]))
    for ip in all_ips:
        ip_id = _id("ip", ip)
        record = intelligence_by_ip.get(ip)
        _add_node(nodes, ip_id, "IP", ip, record.model_dump() if record else {"ip": ip})
        if ip in email.ipv4_addresses:
            _add_edge(edges, email_id, ip_id, "contains_ip")
        for domain, observed_ips in received_domain_to_ips.items():
            if ip in observed_ips:
                _add_edge(edges, domain_ids[domain], ip_id, "resolved_or_relayed_to")
        if record and record.source == "dns_resolved":
            for domain in record.related_domains:
                if domain in domain_ids:
                    _add_edge(edges, domain_ids[domain], ip_id, "dns_resolved_to")
        if record and record.probable_infrastructure_location:
            location = record.probable_infrastructure_location
            location_key = "|".join(str(value or "") for value in (location.country, location.city, location.latitude, location.longitude))
            location_id = _id("location", location_key)
            label = ", ".join(value for value in (location.city, location.country) if value) or "Unknown location"
            _add_node(
                nodes, location_id, "LOCATION", label,
                {**location.model_dump(), "label": "Probable Infrastructure Location", "disclaimer": "This identifies probable network infrastructure location, not a person's physical location."},
            )
            _add_edge(edges, ip_id, location_id, "probable_infrastructure_location")

    return ThreatGraph(nodes=list(nodes.values()), edges=list(edges.values()))


def _email_id(email: ParsedEmail) -> str:
    identity = email.message_id or "|".join(value or "" for value in (email.subject, email.date, email.from_[0].address if email.from_ else None))
    return _id("email", identity)


def _id(prefix: str, value: str) -> str:
    return f"{prefix}:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:16]}"


def _add_node(nodes: dict[str, GraphNode], node_id: str, node_type: str, label: str, metadata: dict) -> None:
    nodes.setdefault(node_id, GraphNode(id=node_id, type=node_type, label=label, metadata=metadata))


def _add_edge(edges: dict[str, GraphEdge], source: str, target: str, relationship: str) -> None:
    edge_id = _id("edge", f"{source}|{relationship}|{target}")
    edges.setdefault(edge_id, GraphEdge(id=edge_id, source=source, target=target, relationship=relationship))
