from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


class EmailAddress(BaseModel):
    display_name: str | None = None
    address: str | None = None
    domain: str | None = None


class AuthenticationCheck(BaseModel):
    result: str
    source: str
    raw: str


class Attachment(BaseModel):
    filename: str | None = None
    content_type: str
    content_disposition: str | None = None
    size_bytes: int


class Indicator(BaseModel):
    name: str
    severity: str
    explanation: str
    score_contribution: int


class RiskAssessment(BaseModel):
    risk_score: int = Field(ge=0, le=100)
    indicators: list[Indicator] = Field(default_factory=list)


class GeminiAnalysis(BaseModel):
    classification: Literal[
        "LEGITIMATE",
        "SUSPICIOUS",
        "PHISHING",
        "IMPERSONATION",
        "BUSINESS_EMAIL_COMPROMISE",
        "MALWARE",
    ]
    confidence: int = Field(ge=0, le=100)
    threat_categories: list[str] = Field(default_factory=list)
    explanation: str
    recommended_action: Literal["ALLOW", "MONITOR", "QUARANTINE", "BLOCK"]


class AIAnalysis(BaseModel):
    """Optional semantic layer; deterministic analysis is always available."""

    available: bool
    result: GeminiAnalysis | None = None


class ParsedEmail(BaseModel):
    """Normalized email content, fully derived from the uploaded EML file."""

    model_config = ConfigDict(populate_by_name=True)

    headers: dict[str, list[str]]
    from_: list[EmailAddress] = Field(default_factory=list, serialization_alias="from")
    to: list[EmailAddress] = Field(default_factory=list)
    reply_to: list[EmailAddress] = Field(default_factory=list)
    return_path: list[EmailAddress] = Field(default_factory=list)
    subject: str | None = None
    date: str | None = None
    message_id: str | None = None
    received_headers: list[str] = Field(default_factory=list)
    authentication_results: list[str] = Field(default_factory=list)
    spf: list[AuthenticationCheck] = Field(default_factory=list)
    dkim: list[AuthenticationCheck] = Field(default_factory=list)
    dmarc: list[AuthenticationCheck] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    ipv4_addresses: list[str] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)
    plain_text_body: str | None = None
    html_body: str | None = None


class EmailDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    headers: dict[str, list[str]]
    from_: list[EmailAddress] = Field(default_factory=list, serialization_alias="from")
    to: list[EmailAddress] = Field(default_factory=list)
    reply_to: list[EmailAddress] = Field(default_factory=list)
    return_path: list[EmailAddress] = Field(default_factory=list)
    subject: str | None = None
    date: str | None = None
    message_id: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    plain_text_body: str | None = None
    html_body: str | None = None


class TechnicalAuthentication(BaseModel):
    authentication_results: list[str] = Field(default_factory=list)
    spf: list[AuthenticationCheck] = Field(default_factory=list)
    dkim: list[AuthenticationCheck] = Field(default_factory=list)
    dmarc: list[AuthenticationCheck] = Field(default_factory=list)
    received_headers: list[str] = Field(default_factory=list)


class ProbableInfrastructureLocation(BaseModel):
    """Network-associated location, not an assertion of a person's physical location."""

    country: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    isp: str | None = None
    asn: str | int | None = None
    organization: str | None = None


class IPIntelligence(BaseModel):
    ip: str
    address_class: Literal["public", "private", "reserved", "documentation", "invalid"]
    eligible_for_lookup: bool
    lookup_available: bool
    source: Literal["observed_email", "dns_resolved"] = "observed_email"
    related_domains: list[str] = Field(default_factory=list)
    probable_infrastructure_location: ProbableInfrastructureLocation | None = None


class GraphNode(BaseModel):
    id: str
    type: Literal["EMAIL", "SENDER", "REPLY_TO", "DOMAIN", "URL", "IP", "LOCATION"]
    label: str
    metadata: dict[str, object] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str


class ThreatGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class RelayTimelineEvent(BaseModel):
    sequence: int = Field(ge=1)
    timestamp: str | None = None
    hostname: str | None = None
    ip: str | None = None
    source: str | None = None
    destination: str | None = None
    raw_header: str
    disclaimer: str


class CompleteAnalyzeResponse(BaseModel):
    case_id: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    classification: Literal[
        "LEGITIMATE",
        "SUSPICIOUS",
        "PHISHING",
        "IMPERSONATION",
        "BUSINESS_EMAIL_COMPROMISE",
        "MALWARE",
    ]
    confidence: int = Field(ge=0, le=100)
    confidence_source: Literal["ai_semantic", "deterministic_fallback"]
    email: EmailDetails
    authentication: TechnicalAuthentication
    indicators: list[Indicator] = Field(default_factory=list)
    ai_analysis: AIAnalysis
    urls: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    ips: list[str] = Field(default_factory=list)
    ip_intelligence: list[IPIntelligence] = Field(default_factory=list)
    timeline: list[RelayTimelineEvent] = Field(default_factory=list)
    threat_graph: ThreatGraph


class CaseCreateRequest(BaseModel):
    case_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filename: str
    risk_score: int = Field(ge=0, le=100)
    classification: Literal[
        "LEGITIMATE", "SUSPICIOUS", "PHISHING", "IMPERSONATION", "BUSINESS_EMAIL_COMPROMISE", "MALWARE"
    ]
    confidence: int | None = Field(default=None, ge=0, le=100)
    summary: str
    indicators: list[Indicator] = Field(default_factory=list)
    analysis: CompleteAnalyzeResponse | None = None


class StoredCase(CaseCreateRequest):
    pass
