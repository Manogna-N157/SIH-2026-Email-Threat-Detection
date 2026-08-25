"""Indicator definitions and deterministic matching patterns."""

from __future__ import annotations

import re

from app.schemas import Indicator


FAILED_AUTH_RESULTS = {"fail", "softfail", "permerror", "temperror"}
SUSPICIOUS_ATTACHMENT_EXTENSIONS = {
    ".bat", ".cmd", ".com", ".exe", ".hta", ".iso", ".js", ".lnk", ".msi", ".ps1", ".scr", ".vbs",
}
SUSPICIOUS_URL_SHORTENERS = {"bit.ly", "cutt.ly", "goo.gl", "is.gd", "rb.gy", "tinyurl.com", "t.co"}

CREDENTIAL_PATTERN = re.compile(
    r"\b(?:password|passcode|credential(?:s)?|sign[ -]?in|log[ -]?in|verify (?:your )?account|confirm (?:your )?account)\b",
    re.IGNORECASE,
)
PAYMENT_PATTERN = re.compile(
    r"\b(?:wire transfer|bank (?:account|details)|payment(?: details)?|invoice|remit(?:tance)?|beneficiary|gift cards?)\b",
    re.IGNORECASE,
)
URGENCY_PATTERN = re.compile(
    r"\b(?:urgent|immediately|asap|action required|final (?:notice|warning)|within \d+ hours?|suspended|expire[sd]?)\b",
    re.IGNORECASE,
)
BEC_PATTERN = re.compile(
    r"\b(?:wire transfer|beneficiary|bank details|gift cards?|keep (?:this )?confidential|do not call|do not (?:tell|contact))\b",
    re.IGNORECASE,
)
IMPERSONATION_PATTERN = re.compile(
    r"\b(?:ceo|chief executive|cfo|chief financial|managing director|it support|help ?desk)\b",
    re.IGNORECASE,
)


def make_indicator(name: str, severity: str, explanation: str, score: int) -> Indicator:
    return Indicator(name=name, severity=severity, explanation=explanation, score_contribution=score)
