from app.email_parser import parse_eml
from app.schemas import IPIntelligence, ProbableInfrastructureLocation
from app.threat_graph import build_threat_graph


def test_graph_contains_stable_nodes_and_observed_relationships() -> None:
    email = parse_eml(
        b"""From: Billing <billing@example.com>
Reply-To: Accounts <accounts@example.net>
Message-ID: <graph-test@example.com>
Subject: Review invoice
Received: from relay.example.org (relay.example.org [8.8.8.8]) by mx.company.test
Content-Type: text/plain; charset=utf-8

Review https://portal.example.com/invoice."""
    )
    intelligence = [
        IPIntelligence(ip="8.8.8.8", address_class="public", eligible_for_lookup=True, lookup_available=True,
            probable_infrastructure_location=ProbableInfrastructureLocation(country="United States", city="Mountain View", latitude=37.4, longitude=-122.1, isp="Google LLC", asn=15169, organization="Google LLC"))
    ]

    first = build_threat_graph(email, intelligence)
    second = build_threat_graph(email, intelligence)
    node_types = {node.type for node in first.nodes}
    relationships = {edge.relationship for edge in first.edges}

    assert first == second
    assert {"EMAIL", "SENDER", "REPLY_TO", "DOMAIN", "URL", "IP", "LOCATION"}.issubset(node_types)
    assert {"sent_by", "replies_to", "references_domain", "contains_url", "resolved_or_relayed_to", "probable_infrastructure_location"}.issubset(relationships)
    assert all(node.id and node.label for node in first.nodes)
    assert all(edge.id and edge.source and edge.target for edge in first.edges)


def test_graph_does_not_create_location_node_without_intelligence() -> None:
    email = parse_eml(
        b"""From: sender@example.com
Received: from relay.example.org (relay.example.org [203.0.113.5]) by mx.test
Content-Type: text/plain

Hello"""
    )

    graph = build_threat_graph(email, [])

    assert "IP" in {node.type for node in graph.nodes}
    assert "LOCATION" not in {node.type for node in graph.nodes}


def test_dns_resolved_ip_graph_edge_is_domain_evidence_not_sender_evidence() -> None:
    email = parse_eml(
        b"""From: sender@example.com
Content-Type: text/plain

Visit https://portal.example.test/login"""
    )
    intelligence = [
        IPIntelligence(
            ip="8.8.8.8", address_class="public", eligible_for_lookup=True,
            lookup_available=False, source="dns_resolved", related_domains=["portal.example.test"],
        )
    ]

    graph = build_threat_graph(email, intelligence)
    ip_node = next(node for node in graph.nodes if node.type == "IP")
    ip_edges = [edge for edge in graph.edges if edge.target == ip_node.id]

    assert {edge.relationship for edge in ip_edges} == {"dns_resolved_to"}
