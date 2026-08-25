"""Composition of parser, deterministic rules, and optional semantic analysis."""

from __future__ import annotations

from uuid import uuid4

from app.schemas import (
    AIAnalysis,
    CompleteAnalyzeResponse,
    EmailDetails,
    GeminiAnalysis,
    IPIntelligence,
    ParsedEmail,
    RiskAssessment,
    TechnicalAuthentication,
)
from app.threat_graph import build_threat_graph
from app.relay_timeline import build_relay_timeline
from app.risk_engine import get_risk_level
from app.confidence_engine import calculate_deterministic_confidence


def build_combined_result(
    parsed_email: ParsedEmail,
    risk_assessment: RiskAssessment,
    semantic_analysis: GeminiAnalysis | None,
    ip_intelligence: list[IPIntelligence],
) -> CompleteAnalyzeResponse:
    """Assemble analysis layers without allowing AI to modify the risk score."""
    classification = semantic_analysis.classification if semantic_analysis else _fallback_classification(risk_assessment)
    if semantic_analysis:
        confidence = semantic_analysis.confidence
        confidence_source = "ai_semantic"
    else:
        confidence = calculate_deterministic_confidence(
            risk_assessment.risk_score,
            classification,
            risk_assessment.indicators,
        )
        confidence_source = "deterministic_fallback"
    return CompleteAnalyzeResponse(
        case_id=str(uuid4()),
        risk_score=risk_assessment.risk_score,
        risk_level=get_risk_level(risk_assessment.risk_score),
        classification=classification,
        confidence=confidence,
        confidence_source=confidence_source,
        email=EmailDetails(
            headers=parsed_email.headers,
            from_=parsed_email.from_,
            to=parsed_email.to,
            reply_to=parsed_email.reply_to,
            return_path=parsed_email.return_path,
            subject=parsed_email.subject,
            date=parsed_email.date,
            message_id=parsed_email.message_id,
            attachments=parsed_email.attachments,
            plain_text_body=parsed_email.plain_text_body,
            html_body=parsed_email.html_body,
        ),
        authentication=TechnicalAuthentication(
            authentication_results=parsed_email.authentication_results,
            spf=parsed_email.spf,
            dkim=parsed_email.dkim,
            dmarc=parsed_email.dmarc,
            received_headers=parsed_email.received_headers,
        ),
        indicators=risk_assessment.indicators,
        ai_analysis=AIAnalysis(available=semantic_analysis is not None, result=semantic_analysis),
        urls=parsed_email.urls,
        domains=parsed_email.domains,
        ips=parsed_email.ipv4_addresses,
        ip_intelligence=ip_intelligence,
        timeline=build_relay_timeline(parsed_email),
        threat_graph=build_threat_graph(parsed_email, ip_intelligence),
    )


def _fallback_classification(risk_assessment: RiskAssessment) -> str:
    """Provide a transparent non-AI classification when Gemini is unavailable."""
    indicator_names = {indicator.name for indicator in risk_assessment.indicators}
    if "Suspicious attachment" in indicator_names:
        return "MALWARE"
    if "BEC indicator" in indicator_names:
        return "BUSINESS_EMAIL_COMPROMISE"
    if "Display-name impersonation" in indicator_names:
        return "IMPERSONATION"
    if "Credential request" in indicator_names:
        return "PHISHING"
    return "SUSPICIOUS" if risk_assessment.risk_score else "LEGITIMATE"
