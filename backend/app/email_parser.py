"""Safe, local parsing utilities for RFC 5322 EML messages."""

from __future__ import annotations

import ipaddress
import re
from collections import defaultdict
from email import policy
from email.headerregistry import Address
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses
from typing import Iterable
from urllib.parse import urlsplit

from app.schemas import Attachment, AuthenticationCheck, EmailAddress, ParsedEmail


URL_PATTERN = re.compile(r"(?i)\b(?:https?://|www\.)[^\s<>\"']+")
BARE_WEB_REFERENCE_PATTERN = re.compile(
    r"(?i)(?<![@\w.-])(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{1,62}(?:/[^\s<>\"']*)?"
)
IPV4_PATTERN = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
EMAIL_ADDRESS_PATTERN = re.compile(
    r"(?i)(?<![\w.+-])([a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+)"
)
AUTH_RESULT_PATTERN = re.compile(
    r"\b(spf|dkim|dmarc)\s*=\s*([a-zA-Z0-9_-]+)", re.IGNORECASE
)
AUTH_STATUS_PATTERN = re.compile(
    r"\b(pass|fail|softfail|neutral|none|temperror|permerror)\b", re.IGNORECASE
)
RECOVERABLE_HEADER_NAMES = {
    b"from", b"to", b"cc", b"bcc", b"reply-to", b"return-path", b"subject", b"date", b"message-id",
    b"received", b"received-spf", b"authentication-results", b"content-type", b"content-transfer-encoding",
    b"mime-version", b"x-originating-ip",
}


def parse_eml(raw_email: bytes) -> ParsedEmail:
    """Parse an EML byte stream without contacting external services."""
    try:
        message = BytesParser(policy=policy.default).parsebytes(_recover_common_header_delimiters(raw_email))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("The uploaded file could not be parsed as an EML message.") from exc

    headers = _collect_headers(message)
    plain_text_body, html_body, attachments = _extract_content(message)
    # Header fields can contain important routing or authentication IP evidence
    # (for example Received-SPF, X-Originating-IP, and Authentication-Results).
    header_text = "\n".join(value for values in headers.values() for value in values)
    body_text = "\n".join(value for value in (plain_text_body, html_body) if value)
    searchable_text = "\n".join(value for value in (body_text, header_text) if value)
    # Fully formed URLs can occur in content or headers. Bare domain-like web
    # references are only recovered from the message body, preventing ordinary
    # sender/recipient addresses from being misrepresented as URLs.
    urls = _deduplicate([*_extract_urls(searchable_text), *_extract_bare_web_references(body_text)])

    address_groups = (
        _addresses(message, "From"),
        _addresses(message, "To"),
        _addresses(message, "Reply-To"),
        _addresses(message, "Return-Path"),
    )
    address_domains = [address.domain for group in address_groups for address in group if address.domain]

    authentication_results = _all_header_values(message, "Authentication-Results")
    spf_checks = _auth_checks(authentication_results, "spf", "authentication-results")
    spf_checks.extend(_received_spf_checks(message))

    return ParsedEmail(
        headers=headers,
        from_=_addresses(message, "From"),
        to=_addresses(message, "To"),
        reply_to=_addresses(message, "Reply-To"),
        return_path=_addresses(message, "Return-Path"),
        subject=_first_header_value(message, "Subject"),
        date=_first_header_value(message, "Date"),
        message_id=_first_header_value(message, "Message-ID"),
        received_headers=_all_header_values(message, "Received"),
        authentication_results=authentication_results,
        spf=spf_checks,
        dkim=_auth_checks(authentication_results, "dkim", "authentication-results"),
        dmarc=_auth_checks(authentication_results, "dmarc", "authentication-results"),
        urls=urls,
        domains=_deduplicate([*_domains_from_urls(urls), *address_domains]),
        ipv4_addresses=_extract_ipv4(searchable_text),
        attachments=attachments,
        plain_text_body=plain_text_body,
        html_body=html_body,
    )


def _recover_common_header_delimiters(raw_email: bytes) -> bytes:
    """Recover common missing-colon header typos before RFC parsing.

    A compliant RFC 5322 message is returned byte-for-byte unchanged. This
    narrow recovery only applies in the leading header block and only to known
    field names, allowing useful forensic extraction from otherwise readable
    exported messages without fabricating any values.
    """
    lines = raw_email.splitlines(keepends=True)
    recovered: list[bytes] = []
    in_header_block = True

    for line in lines:
        line_without_ending = line.rstrip(b"\r\n")
        ending = line[len(line_without_ending):]
        if in_header_block and not line_without_ending:
            in_header_block = False
            recovered.append(line)
            continue
        if not in_header_block or line_without_ending[:1] in {b" ", b"\t"}:
            recovered.append(line)
            continue

        field_name, separator, value = line_without_ending.partition(b" ")
        if not separator:
            field_name, separator, value = line_without_ending.partition(b"\t")
        if (
            separator
            and b":" not in field_name
            and field_name.lower() in RECOVERABLE_HEADER_NAMES
        ):
            if field_name.lower() == b"content-type":
                value = re.sub(rb"^textplain(?=\s*;|$)", b"text/plain", value, flags=re.IGNORECASE)
                value = re.sub(rb"^texthtml(?=\s*;|$)", b"text/html", value, flags=re.IGNORECASE)
            recovered.append(field_name + b": " + value + ending)
        else:
            recovered.append(line)

    return b"".join(recovered)


def _collect_headers(message: EmailMessage) -> dict[str, list[str]]:
    """Preserve every header value, including duplicate header names."""
    grouped: defaultdict[str, list[str]] = defaultdict(list)
    for name, value in message.raw_items():
        grouped[name.lower()].append(str(value))
    return dict(grouped)


def _all_header_values(message: EmailMessage, name: str) -> list[str]:
    return [str(value) for value in message.get_all(name, [])]


def _first_header_value(message: EmailMessage, name: str) -> str | None:
    values = _all_header_values(message, name)
    return values[0] if values else None


def _addresses(message: EmailMessage, name: str) -> list[EmailAddress]:
    addresses: list[EmailAddress] = []
    for header in message.get_all(name, []):
        parsed_addresses: Iterable[Address] = getattr(header, "addresses", ())
        malformed_addresses = [address for address in parsed_addresses if " " in (address.addr_spec or "")]
        if malformed_addresses:
            recovered = _recover_embedded_addresses(str(header))
            if recovered:
                addresses.extend(recovered)
                continue
        for address in parsed_addresses:
            addresses.append(
                EmailAddress(
                    display_name=address.display_name or None,
                    address=address.addr_spec or None,
                    domain=address.domain or None,
                )
            )
        if not parsed_addresses:
            # Return-Path and malformed address headers are often unstructured.
            for display_name, addr_spec in getaddresses([str(header)]):
                local_part, separator, domain = addr_spec.rpartition("@")
                addresses.append(
                    EmailAddress(
                        display_name=display_name or None,
                        address=addr_spec or None,
                        domain=domain.lower() if separator and local_part else None,
                    )
                )
    return addresses


def _recover_embedded_addresses(value: str) -> list[EmailAddress]:
    """Recover visible mailbox tokens from a non-standard unbracketed header."""
    recovered: list[EmailAddress] = []
    for match in EMAIL_ADDRESS_PATTERN.finditer(value):
        address = match.group(1)
        local_part, _, domain = address.rpartition("@")
        display_name = value[:match.start()].strip(" \t\"'<") or None
        recovered.append(
            EmailAddress(
                display_name=display_name,
                address=address,
                domain=domain.lower() if local_part else None,
            )
        )
    return recovered


def _extract_content(message: EmailMessage) -> tuple[str | None, str | None, list[Attachment]]:
    plain_text: str | None = None
    html: str | None = None
    attachments: list[Attachment] = []

    parts = message.walk() if message.is_multipart() else (message,)
    for part in parts:
        if part.is_multipart():
            continue
        filename = part.get_filename()
        disposition = part.get_content_disposition()
        if disposition == "attachment" or filename:
            payload = part.get_payload(decode=True) or b""
            attachments.append(
                Attachment(
                    filename=filename,
                    content_type=part.get_content_type(),
                    content_disposition=disposition,
                    size_bytes=len(payload),
                )
            )
            continue

        content_type = part.get_content_type()
        if content_type == "text/plain" and plain_text is None:
            plain_text = _decode_part(part)
        elif content_type == "text/html" and html is None:
            html = _decode_part(part)
    return plain_text, html, attachments


def _decode_part(part: EmailMessage) -> str:
    try:
        content = part.get_content()
        return content if isinstance(content, str) else content.decode("utf-8", errors="replace")
    except (LookupError, UnicodeError, ValueError):
        payload = part.get_payload(decode=True) or b""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")


def _auth_checks(values: list[str], method: str, source: str) -> list[AuthenticationCheck]:
    checks: list[AuthenticationCheck] = []
    for value in values:
        for found_method, result in AUTH_RESULT_PATTERN.findall(value):
            if found_method.lower() == method:
                checks.append(AuthenticationCheck(result=result.lower(), source=source, raw=value))
    return checks


def _received_spf_checks(message: EmailMessage) -> list[AuthenticationCheck]:
    checks: list[AuthenticationCheck] = []
    for value in _all_header_values(message, "Received-SPF"):
        match = AUTH_STATUS_PATTERN.search(value)
        if match:
            checks.append(
                AuthenticationCheck(result=match.group(1).lower(), source="received-spf", raw=value)
            )
    return checks


def _extract_urls(text: str) -> list[str]:
    return _deduplicate(match.group(0).rstrip(".,;:!?)]}\"'") for match in URL_PATTERN.finditer(text))


def _extract_bare_web_references(text: str) -> list[str]:
    """Extract body-only domain references when a sender omitted a scheme."""
    url_spans = [match.span() for match in URL_PATTERN.finditer(text)]
    return _deduplicate(
        match.group(0).rstrip(".,;:!?)]}\"'")
        for match in BARE_WEB_REFERENCE_PATTERN.finditer(text)
        if not any(start <= match.start() < end for start, end in url_spans)
    )


def _domains_from_urls(urls: list[str]) -> list[str]:
    domains: list[str] = []
    for url in urls:
        parsed = urlsplit(url if "://" in url else f"http://{url}")
        if parsed.hostname:
            domains.append(parsed.hostname.lower())
    return domains


def _extract_ipv4(text: str) -> list[str]:
    addresses: list[str] = []
    for match in IPV4_PATTERN.finditer(text):
        candidate = match.group(0)
        try:
            if isinstance(ipaddress.ip_address(candidate), ipaddress.IPv4Address):
                addresses.append(candidate)
        except ValueError:
            continue
    return _deduplicate(addresses)


def _deduplicate(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
