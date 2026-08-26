"""Local, deterministic rules for common email threat indicators."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.indicators import (
    BEC_PATTERN,
    CREDENTIAL_PATTERN,
    FAILED_AUTH_RESULTS,
    IMPERSONATION_PATTERN,
    PAYMENT_PATTERN,
    SUSPICIOUS_ATTACHMENT_EXTENSIONS,
    SUSPICIOUS_URL_SHORTENERS,
    URGENCY_PATTERN,
    make_indicator,
)
from app.risk_engine import calculate_risk
from app.schemas import Indicator, ParsedEmail, RiskAssessment


def analyze_email_rules(email: ParsedEmail) -> RiskAssessment:
    """Generate fixed-rule indicators and a reproducible score for a parsed email."""
    indicators: list[Indicator] = []
    _add_authentication_indicators(email, indicators)
    _add_address_indicators(email, indicators)
    _add_url_indicators(email, indicators)
    _add_content_indicators(email, indicators)
    _add_attachment_indicators(email, indicators)
    _add_display_name_indicators(email, indicators)
    return calculate_risk(indicators)


def _add_authentication_indicators(email: ParsedEmail, indicators: list[Indicator]) -> None:
    checks = (("SPF failure", email.spf, 15), ("DKIM failure", email.dkim, 15), ("DMARC failure", email.dmarc, 20))
    for name, results, score in checks:
        failed = next((check for check in results if check.result.lower() in FAILED_AUTH_RESULTS), None)
        if failed:
            indicators.append(make_indicator(name, "high", f"{name.split()[0]} returned '{failed.result}'.", score))


def _add_address_indicators(email: ParsedEmail, indicators: list[Indicator]) -> None:
    sender_domain = _first_domain(email.from_)
    reply_domain = _first_domain(email.reply_to)
    return_path_domain = _first_domain(email.return_path)
    if sender_domain and reply_domain and sender_domain != reply_domain:
        indicators.append(
            make_indicator(
                "Reply-To mismatch", "medium", f"From uses {sender_domain}, but Reply-To uses {reply_domain}.", 12
            )
        )
    if sender_domain and return_path_domain and sender_domain != return_path_domain:
        indicators.append(
            make_indicator(
                "Sender/domain mismatch", "medium", f"From uses {sender_domain}, but Return-Path uses {return_path_domain}.", 10
            )
        )


def _add_url_indicators(email: ParsedEmail, indicators: list[Indicator]) -> None:
    suspicious_urls = [url for url in email.urls if _is_suspicious_url(url)]
    if suspicious_urls:
        indicators.append(
            make_indicator("Suspicious URL", "high", f"Found {len(suspicious_urls)} suspicious URL(s).", 12)
        )
    suspicious_domains = [domain for domain in email.domains if _is_suspicious_domain(domain)]
    if suspicious_domains:
        indicators.append(
            make_indicator(
                "Suspicious domain pattern", "medium", f"Found suspicious domain pattern(s): {', '.join(suspicious_domains)}.", 10
            )
        )
    suspicious_sender_domains = [
        address.domain for address in email.from_ if address.domain and _is_suspicious_domain(address.domain)
    ]
    if suspicious_urls and suspicious_sender_domains and CREDENTIAL_PATTERN.search(_content(email)):
        indicators.append(
            make_indicator(
                "Credential-harvesting link",
                "high",
                "Message combines credential requests with a suspicious web link.",
                15,
            )
        )


def _add_content_indicators(email: ParsedEmail, indicators: list[Indicator]) -> None:
    content = _content(email)
    has_payment = bool(PAYMENT_PATTERN.search(content))
    if CREDENTIAL_PATTERN.search(content):
        indicators.append(make_indicator("Credential request", "high", "Message asks for login or account credentials.", 15))
    if has_payment:
        indicators.append(make_indicator("Payment request", "high", "Message includes payment or banking language.", 15))
    if BEC_PATTERN.search(content) and has_payment:
        indicators.append(make_indicator("BEC indicator", "high", "Message combines payment language with business-email-compromise cues.", 18))
    if URGENCY_PATTERN.search(content):
        indicators.append(make_indicator("Urgency/social engineering", "medium", "Message uses urgency or pressure language.", 8))


def _add_attachment_indicators(email: ParsedEmail, indicators: list[Indicator]) -> None:
    names = [attachment.filename.lower() for attachment in email.attachments if attachment.filename]
    suspicious = [name for name in names if _has_suspicious_attachment_name(name)]
    if suspicious:
        indicators.append(
            make_indicator("Suspicious attachment", "high", f"Suspicious attachment name(s): {', '.join(suspicious)}.", 18)
        )


def _add_display_name_indicators(email: ParsedEmail, indicators: list[Indicator]) -> None:
    for sender in email.from_:
        if sender.display_name and IMPERSONATION_PATTERN.search(sender.display_name):
            indicators.append(
                make_indicator(
                    "Display-name impersonation",
                    "high",
                    f"Sender display name '{sender.display_name}' claims a sensitive business role.",
                    12,
                )
            )
            return


def _first_domain(addresses: list) -> str | None:
    return next((address.domain.lower() for address in addresses if address.domain), None)


def _is_suspicious_url(url: str) -> bool:
    parsed = urlsplit(url if "://" in url else f"http://{url}")
    hostname = (parsed.hostname or "").lower()
    return (
        url.lower().startswith("http://")
        or "@" in parsed.netloc
        or hostname in SUSPICIOUS_URL_SHORTENERS
        or hostname.replace(".", "").isdigit()
        or _is_suspicious_domain(hostname)
    )


def _is_suspicious_domain(domain: str) -> bool:
    labels = domain.lower().split(".")
    first_label = labels[0] if labels else ""
    digit_count = sum(char.isdigit() for char in first_label)
    return (
        domain.lower().startswith("xn--")
        or first_label.count("-") >= 2
        or digit_count >= 3
        or (digit_count > 0 and "-" in first_label)
    )


def _content(email: ParsedEmail) -> str:
    return "\n".join(part for part in (email.subject, email.plain_text_body, email.html_body) if part).lower()


def _has_suspicious_attachment_name(name: str) -> bool:
    suffix = "." + name.rsplit(".", 1)[1] if "." in name else ""
    stem = name[: -len(suffix)] if suffix else name
    return suffix in SUSPICIOUS_ATTACHMENT_EXTENSIONS or "." in stem
