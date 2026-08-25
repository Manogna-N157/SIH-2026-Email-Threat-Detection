import asyncio
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response

from app import case_storage
from app.analysis_pipeline import build_combined_result
from app.ai.gemini_analyzer import analyze_with_gemini
from app.email_parser import parse_eml
from app.ip_intelligence import resolve_domain_intelligence, resolve_ip_intelligence
from app.report_generator import generate_case_pdf
from app.rule_engine import analyze_email_rules
from app.schemas import CaseCreateRequest, CompleteAnalyzeResponse, HealthResponse, StoredCase


logger = logging.getLogger(__name__)
DNS_FALLBACK_TIMEOUT_SECONDS = 3

app = FastAPI(
    title="AI-Powered Email Threat Detection API",
    version="0.1.0",
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Confirm that the API is available."""
    return HealthResponse(status="ok")


@app.post("/api/analyze", response_model=CompleteAnalyzeResponse)
async def analyze_email(file: UploadFile = File(...)) -> CompleteAnalyzeResponse:
    """Run the complete local and optional semantic EML analysis pipeline."""
    if not file.filename or not file.filename.lower().endswith(".eml"):
        raise HTTPException(
            status_code=400,
            detail="Only .eml email files are accepted.",
        )

    raw_email = await file.read()
    try:
        parsed_email = parse_eml(raw_email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    risk_assessment = analyze_email_rules(parsed_email)
    semantic_analysis = analyze_with_gemini(parsed_email, risk_assessment)
    ip_intelligence = await asyncio.to_thread(resolve_ip_intelligence, parsed_email.ipv4_addresses)
    if not parsed_email.ipv4_addresses:
        # DNS-derived records are explicitly marked as such and are never treated
        # as sender IPs. This is useful only when the EML exposes a domain/URL but
        # no IP evidence at all.
        ip_intelligence = await _resolve_dns_fallback(parsed_email.domains)
    return build_combined_result(parsed_email, risk_assessment, semantic_analysis, ip_intelligence)


async def _resolve_dns_fallback(domains: list[str]):
    """Keep DNS-derived infrastructure evidence optional and bounded."""
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(resolve_domain_intelligence, domains),
            timeout=DNS_FALLBACK_TIMEOUT_SECONDS,
        )
    except (TimeoutError, OSError, ValueError):
        logger.warning("DNS infrastructure resolution was unavailable; continuing without DNS evidence.")
        return []


@app.post("/api/cases", response_model=StoredCase, status_code=201)
async def store_case(case: CaseCreateRequest) -> StoredCase:
    """Persist a selected analysis case without storing credentials or API secrets."""
    try:
        return await asyncio.to_thread(case_storage.create_case, case)
    except case_storage.CaseAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="A case with this case_id already exists.") from exc


@app.get("/api/cases", response_model=list[StoredCase])
async def list_stored_cases() -> list[StoredCase]:
    """List stored cases, newest first."""
    return await asyncio.to_thread(case_storage.list_cases)


@app.get("/api/cases/{case_id}", response_model=StoredCase)
async def get_stored_case(case_id: str) -> StoredCase:
    """Return one stored case by its stable case identifier."""
    case = await asyncio.to_thread(case_storage.get_case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@app.delete("/api/cases/{case_id}")
async def delete_stored_case(case_id: str):
    """Delete a stored case by case_id."""
    deleted = await asyncio.to_thread(case_storage.delete_case, case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found.")
    return {"message": "Case deleted successfully.", "case_id": case_id}


@app.delete("/api/cases")
async def delete_all_stored_cases():
    """Delete all stored cases."""
    count = await asyncio.to_thread(case_storage.delete_all_cases)
    return {"message": f"Successfully deleted {count} case(s).", "count": count}



@app.get("/api/reports/{case_id}/pdf", response_class=Response)
async def get_case_pdf_report(case_id: str) -> Response:
    """Generate a PDF report from a stored case without exposing any secrets."""
    case = await asyncio.to_thread(case_storage.get_case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    report = await asyncio.to_thread(generate_case_pdf, case)
    return Response(
        content=report,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="case-{case_id}-report.pdf"'},
    )
