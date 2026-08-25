"""Professional, minimal forensic PDF reports generated from stored cases."""

from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas import StoredCase
from app.risk_engine import get_risk_level


def generate_case_pdf(case: StoredCase) -> bytes:
    """Generate a report from stored, non-secret case evidence."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=15 * mm, bottomMargin=15 * mm
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#123047")))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#123047"), spaceBefore=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story = [Paragraph("Email Threat Detection - Forensic Report", styles["ReportTitle"]), Spacer(1, 5 * mm)]

    _section(story, styles, "Case overview")
    _table(story, [
        ("Case ID", case.case_id), ("Investigation timestamp", case.timestamp.isoformat()), ("Filename", case.filename),
        ("Risk score", f"{case.risk_score}/100"), ("Risk level", get_risk_level(case.risk_score)),
        ("Classification", case.classification), ("Confidence", _confidence_label(case.confidence)),
        ("Summary", case.summary),
    ], styles)

    analysis = case.analysis
    _section(story, styles, "Email metadata")
    if analysis:
        email = analysis.email
        _table(story, [
            ("From", _addresses(email.from_)), ("To", _addresses(email.to)), ("Reply-To", _addresses(email.reply_to)),
            ("Return-Path", _addresses(email.return_path)), ("Subject", email.subject or "Not available"),
            ("Date", email.date or "Not available"), ("Message-ID", email.message_id or "Not available"),
        ], styles)
    else:
        _notice(story, styles, "Detailed email metadata was not stored with this case.")

    _section(story, styles, "Authentication results")
    if analysis:
        _table(story, [
            ("SPF", _checks(analysis.authentication.spf)), ("DKIM", _checks(analysis.authentication.dkim)),
            ("DMARC", _checks(analysis.authentication.dmarc)),
        ], styles)
    else:
        _notice(story, styles, "Authentication details were not stored with this case.")

    _section(story, styles, "Security indicators")
    _indicator_table(story, case.indicators, styles)

    _section(story, styles, "URLs, domains, and IPs")
    if analysis:
        _table(story, [("URLs", _join(analysis.urls)), ("Domains", _join(analysis.domains)), ("IPs", _join(analysis.ips))], styles)
    else:
        _notice(story, styles, "Network artifacts were not stored with this case.")

    _section(story, styles, "Probable Infrastructure Location")
    if analysis:
        infrastructure = []
        for record in analysis.ip_intelligence:
            location = record.probable_infrastructure_location
            if location:
                place = ", ".join(filter(None, [location.city, location.region, location.country])) or "Unknown"
                infrastructure.append((record.ip, record.source, place, location.isp or "Unknown", str(location.asn or "Unknown"), location.organization or "Unknown"))
        _infrastructure_table(story, infrastructure, styles)
    else:
        _notice(story, styles, "Infrastructure intelligence was not stored with this case.")
    _notice(story, styles, "Infrastructure geolocation identifies probable network infrastructure, not an attacker's physical location.")

    _section(story, styles, "AI semantic analysis")
    if analysis and analysis.ai_analysis.result:
        ai = analysis.ai_analysis.result
        _table(story, [("Explanation", ai.explanation), ("Recommended action", ai.recommended_action), ("Threat categories", _join(ai.threat_categories))], styles)
    else:
        _notice(story, styles, "AI semantic analysis was unavailable or was not stored with this case.")

    _section(story, styles, "Relay timeline")
    if analysis:
        _timeline_table(story, analysis.timeline, styles)
    else:
        _notice(story, styles, "Relay timeline was not stored with this case.")

    _section(story, styles, "Threat graph summary")
    if analysis:
        types = sorted({node.type for node in analysis.threat_graph.nodes})
        _table(story, [("Nodes", str(len(analysis.threat_graph.nodes))), ("Edges", str(len(analysis.threat_graph.edges))), ("Node types", _join(types))], styles)
    else:
        _notice(story, styles, "Threat graph data was not stored with this case.")

    document.build(story)
    return buffer.getvalue()


def _section(story: list, styles, title: str) -> None:
    story.append(Paragraph(title, styles["Section"]))


def _table(story: list, rows: list[tuple[str, str]], styles) -> None:
    table = Table([[Paragraph(f"<b>{escape(key)}</b>", styles["Small"]), Paragraph(escape(value), styles["Small"])] for key, value in rows], colWidths=[42 * mm, 136 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF1F5")), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C6D1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.extend([table, Spacer(1, 3 * mm)])


def _indicator_table(story: list, indicators, styles) -> None:
    rows = [[
        Paragraph("<b>Name</b>", styles["Small"]),
        Paragraph("<b>Severity</b>", styles["Small"]),
        Paragraph("<b>Score</b>", styles["Small"]),
        Paragraph("<b>Explanation</b>", styles["Small"]),
    ]]
    rows += [
        [
            Paragraph(escape(item.name), styles["Small"]),
            Paragraph(escape(item.severity), styles["Small"]),
            Paragraph(str(item.score_contribution), styles["Small"]),
            Paragraph(escape(item.explanation), styles["Small"]),
        ]
        for item in indicators
    ]
    table = Table(rows, colWidths=[38 * mm, 24 * mm, 16 * mm, 100 * mm], repeatRows=1)
    table.setStyle(_grid_style())
    story.extend([table, Spacer(1, 3 * mm)])


def _infrastructure_table(story: list, records: list[tuple[str, str, str, str, str, str]], styles) -> None:
    rows = [[Paragraph("<b>IP</b>", styles["Small"]), Paragraph("<b>Evidence source</b>", styles["Small"]), Paragraph("<b>Location</b>", styles["Small"]), Paragraph("<b>ISP</b>", styles["Small"]), Paragraph("<b>ASN</b>", styles["Small"]), Paragraph("<b>Organization</b>", styles["Small"])]]
    rows += [[Paragraph(escape(value), styles["Small"]) for value in record] for record in records]
    if not records:
        rows.append([Paragraph("No probable infrastructure location available.", styles["Small"]), "", "", "", "", ""])
    table = Table(rows, colWidths=[21 * mm, 30 * mm, 37 * mm, 35 * mm, 17 * mm, 38 * mm], repeatRows=1)
    table.setStyle(_grid_style())
    if not records:
        table.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
    story.extend([table, Spacer(1, 3 * mm)])


def _timeline_table(story: list, events, styles) -> None:
    rows = [[Paragraph("<b>#</b>", styles["Small"]), Paragraph("<b>Timestamp</b>", styles["Small"]), Paragraph("<b>Source</b>", styles["Small"]), Paragraph("<b>Destination</b>", styles["Small"]), Paragraph("<b>IP</b>", styles["Small"])]]
    rows += [[Paragraph(str(event.sequence), styles["Small"]), Paragraph(escape(event.timestamp or "Unknown"), styles["Small"]), Paragraph(escape(event.source or "Unknown"), styles["Small"]), Paragraph(escape(event.destination or "Unknown"), styles["Small"]), Paragraph(escape(event.ip or "Unknown"), styles["Small"])] for event in events]
    if not events:
        rows.append([Paragraph("No relay events available.", styles["Small"]), "", "", "", ""])
    table = Table(rows, colWidths=[10 * mm, 47 * mm, 47 * mm, 47 * mm, 27 * mm], repeatRows=1)
    table.setStyle(_grid_style())
    if not events:
        table.setStyle(TableStyle([("SPAN", (0, 1), (-1, 1))]))
    story.extend([table, Spacer(1, 3 * mm)])


def _grid_style() -> TableStyle:
    return TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123047")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#B8C6D1")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)])


def _addresses(addresses) -> str:
    return _join([address.address or address.display_name or "Unknown" for address in addresses])


def _checks(checks) -> str:
    return _join([check.result for check in checks])


def _join(values) -> str:
    return ", ".join(str(value) for value in values) if values else "None"


def _confidence_label(confidence: int | None) -> str:
    return f"{confidence}%" if confidence is not None else "Not available"


def _notice(story: list, styles, text: str) -> None:
    story.extend([Paragraph(escape(text), styles["Small"]), Spacer(1, 3 * mm)])
