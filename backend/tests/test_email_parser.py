from pathlib import Path

from app.email_parser import parse_eml


WORKSPACE_DIR = Path(__file__).resolve().parents[2]


MULTIPART_EMAIL = b"""From: Billing Team <billing@example.com>
From: Backup Sender <backup@example.net>
To: Alice <alice@company.test>, Bob <bob@company.test>
Reply-To: Accounts <accounts@reply.example>
Return-Path: <bounce@example.com>
Subject: Invoice available
Date: Tue, 24 Aug 2026 10:00:00 +0530
Message-ID: <invoice-123@example.com>
Received: from relay.example.com (relay.example.com [203.0.113.10]) by mx.company.test with ESMTP;
Received: from 198.51.100.7 by relay.example.com;
Authentication-Results: mx.company.test; spf=pass smtp.mailfrom=example.com; dkim=pass header.d=example.com; dmarc=pass header.from=example.com
Received-SPF: pass (mx.company.test: domain of example.com designates 203.0.113.10 as permitted sender)
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="outer"

--outer
Content-Type: multipart/alternative; boundary="inner"

--inner
Content-Type: text/plain; charset="utf-8"

Open https://portal.example.com/invoice and www.example.org/help.

--inner
Content-Type: text/html; charset="utf-8"

<p>Open <a href="https://portal.example.com/invoice">your invoice</a>.</p>

--inner--
--outer
Content-Type: application/pdf
Content-Disposition: attachment; filename="invoice.pdf"
Content-Transfer-Encoding: base64

SGVsbG8=
--outer--
"""


def test_parses_multipart_email_with_headers_auth_and_attachment() -> None:
    parsed = parse_eml(MULTIPART_EMAIL)

    assert len(parsed.from_) == 2  # Duplicate headers are preserved.
    assert parsed.from_[0].address == "billing@example.com"
    assert [recipient.address for recipient in parsed.to] == ["alice@company.test", "bob@company.test"]
    assert parsed.reply_to[0].address == "accounts@reply.example"
    assert parsed.return_path[0].address == "bounce@example.com"
    assert parsed.subject == "Invoice available"
    assert parsed.message_id == "<invoice-123@example.com>"
    assert len(parsed.received_headers) == 2
    assert parsed.spf[0].result == "pass"
    assert parsed.dkim[0].result == "pass"
    assert parsed.dmarc[0].result == "pass"
    assert "https://portal.example.com/invoice" in parsed.urls
    assert "www.example.org/help" in parsed.urls
    assert "portal.example.com" in parsed.domains
    assert parsed.ipv4_addresses == ["203.0.113.10", "198.51.100.7"]
    assert parsed.attachments[0].filename == "invoice.pdf"
    assert parsed.attachments[0].size_bytes == 5
    assert "Open https://portal.example.com/invoice" in (parsed.plain_text_body or "")
    assert "portal.example.com" in (parsed.html_body or "")


def test_parses_html_only_email_and_missing_headers() -> None:
    parsed = parse_eml(
        b"""From: sender@example.com
Content-Type: text/html; charset=utf-8

<html><body><a href="http://only-html.example/path">Visit</a></body></html>"""
    )

    assert parsed.subject is None
    assert parsed.to == []
    assert parsed.plain_text_body is None
    assert "only-html.example" in (parsed.html_body or "")
    assert parsed.urls == ["http://only-html.example/path"]


def test_handles_malformed_headers_and_invalid_ipv4_without_crashing() -> None:
    parsed = parse_eml(
        b"""From: Broken Sender <not-an-address
Received: from suspicious.invalid (999.999.999.999) by mx.test
Content-Type: text/plain; charset=unknown-charset

See https://safe.example/test and 300.1.1.1"""
    )

    assert parsed.plain_text_body is not None
    assert parsed.urls == ["https://safe.example/test"]
    assert parsed.ipv4_addresses == []


def test_extracts_ipv4_evidence_from_authentication_and_forensic_headers() -> None:
    parsed = parse_eml(
        b"""From: sender@example.com
Authentication-Results: mx.test; spf=pass smtp.mailfrom=example.com client-ip=8.8.8.8
X-Originating-IP: [1.1.1.1]
X-Forwarded-For: 203.0.113.9
Content-Type: text/plain

Hello"""
    )

    assert parsed.ipv4_addresses == ["8.8.8.8", "1.1.1.1", "203.0.113.9"]


def test_recovers_common_missing_header_delimiters_in_uploaded_eml() -> None:
    """Readable exported EMLs with missing colons retain their actual evidence."""
    parsed = parse_eml((WORKSPACE_DIR / "high_risk_test.eml").read_bytes())

    assert parsed.from_[0].display_name == "Microsoft Security"
    assert parsed.from_[0].address == "security-alert@micros0ft-support.com"
    assert parsed.from_[0].domain == "micros0ft-support.com"
    assert parsed.to[0].address == "employee@example.com"
    assert parsed.subject == "URGENT Your Microsoft 365 Account Will Be Suspended Today"
    assert parsed.date == "Tue, 25 Aug 2026 203000 +0530"
    assert "password" in (parsed.plain_text_body or "").lower()
    assert parsed.html_body is None
    assert parsed.urls == ["httpmicrosoft-account-security-verification.example.comlogin"]
    assert "micros0ft-support.com" in parsed.domains
    assert "httpmicrosoft-account-security-verification.example.comlogin" in parsed.domains
