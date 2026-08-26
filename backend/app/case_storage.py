"""Minimal SQLite persistence for completed email-analysis cases."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from app import evidence_ledger
from app.confidence_engine import calculate_deterministic_confidence
from app.risk_engine import get_risk_level
from app.schemas import CaseCreateRequest, CompleteAnalyzeResponse, EvidenceBlock, Indicator, StoredCase


DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "cases.db"
logger = logging.getLogger(__name__)
_RECENT_ANALYSES: dict[str, CompleteAnalyzeResponse] = {}
RECENT_ANALYSIS_LIMIT = 100


class CaseAlreadyExistsError(Exception):
    """Raised when a caller tries to reuse an existing case ID."""


def remember_analysis(analysis: CompleteAnalyzeResponse) -> None:
    """Retain a completed analysis until its existing case-creation request arrives."""
    if analysis.case_id not in _RECENT_ANALYSES and len(_RECENT_ANALYSES) >= RECENT_ANALYSIS_LIMIT:
        _RECENT_ANALYSES.pop(next(iter(_RECENT_ANALYSES)))
    _RECENT_ANALYSES[analysis.case_id] = analysis


def clear_remembered_analyses() -> None:
    """Test helper and bounded-lifecycle cleanup for transient analysis state."""
    _RECENT_ANALYSES.clear()


def create_case(case: CaseCreateRequest) -> StoredCase:
    _initialize_database()
    stored_case = StoredCase(**_case_with_analysis(case).model_dump())
    try:
        with _connect() as connection:
            connection.execute(
                """
                INSERT INTO cases (
                    case_id, timestamp, filename, risk_score, classification,
                    confidence, summary, indicators_json
                    , analysis_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_case.case_id,
                    stored_case.timestamp.isoformat(),
                    stored_case.filename,
                    stored_case.risk_score,
                    stored_case.classification,
                    stored_case.confidence,
                    stored_case.summary,
                    json.dumps([indicator.model_dump() for indicator in stored_case.indicators]),
                    stored_case.analysis.model_dump_json() if stored_case.analysis else None,
                ),
            )
            evidence_ledger.append_block(connection, stored_case)
    except sqlite3.IntegrityError as exc:
        raise CaseAlreadyExistsError(case.case_id) from exc
    _RECENT_ANALYSES.pop(case.case_id, None)
    return stored_case


def list_cases() -> list[StoredCase]:
    _initialize_database()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT case_id, timestamp, filename, risk_score, classification, confidence, summary, indicators_json, analysis_json "
            "FROM cases ORDER BY timestamp DESC, case_id DESC"
        ).fetchall()
    cases: list[StoredCase] = []
    for row in rows:
        case = _safe_row_to_case(row)
        if case is not None:
            cases.append(case)
    return cases


def get_case(case_id: str) -> StoredCase | None:
    _initialize_database()
    with _connect() as connection:
        row = connection.execute(
            "SELECT case_id, timestamp, filename, risk_score, classification, confidence, summary, indicators_json, analysis_json "
            "FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
    return _safe_row_to_case(row) if row else None


def list_evidence_blocks() -> list[EvidenceBlock]:
    _initialize_database()
    with _connect() as connection:
        return evidence_ledger.list_blocks(connection)


def verify_case_evidence(case_id: str) -> tuple[StoredCase | None, EvidenceBlock | None, bool]:
    """Recreate evidence and validate the requested block plus its chain history."""
    _initialize_database()
    with _connect() as connection:
        row = connection.execute(
            "SELECT case_id, timestamp, filename, risk_score, classification, confidence, summary, indicators_json, analysis_json "
            "FROM cases WHERE case_id = ?",
            (case_id,),
        ).fetchone()
        case = _safe_row_to_case(row) if row else None
        if case is None:
            return None, None, False
        block = evidence_ledger.get_block(connection, case_id)
        if block is None:
            return case, None, False
        evidence_matches = evidence_ledger.evidence_hash(case) == block.evidence_hash
        return case, block, evidence_matches and evidence_ledger.verify_block_chain(connection, block)


def delete_case(case_id: str) -> bool:
    _initialize_database()
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
        return cursor.rowcount > 0


def delete_all_cases() -> int:
    _initialize_database()
    with _connect() as connection:
        cursor = connection.execute("DELETE FROM cases")
        return cursor.rowcount



def _initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                filename TEXT NOT NULL,
                risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
                classification TEXT NOT NULL,
                confidence INTEGER CHECK (confidence BETWEEN 0 AND 100),
                summary TEXT NOT NULL,
                indicators_json TEXT NOT NULL
                , analysis_json TEXT
            )
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(cases)")}
        if "analysis_json" not in columns:
            connection.execute("ALTER TABLE cases ADD COLUMN analysis_json TEXT")
        if next(row for row in connection.execute("PRAGMA table_info(cases)") if row["name"] == "confidence")["notnull"]:
            _migrate_nullable_confidence(connection)
        evidence_ledger.initialize_ledger(connection)


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _row_to_case(row: sqlite3.Row) -> StoredCase:
    analysis = _parse_analysis_snapshot(row["analysis_json"])
    indicators = [Indicator.model_validate(item) for item in json.loads(row["indicators_json"])]
    return StoredCase(
        case_id=row["case_id"],
        timestamp=row["timestamp"],
        filename=row["filename"],
        risk_score=row["risk_score"],
        classification=row["classification"],
        confidence=_stored_confidence(
            row["confidence"], analysis, row["risk_score"], row["classification"], indicators
        ),
        summary=row["summary"],
        indicators=indicators,
        analysis=analysis,
    )


def _safe_row_to_case(row: sqlite3.Row) -> StoredCase | None:
    """Keep one stale database row from failing the entire case-list endpoint."""
    try:
        return _row_to_case(row)
    except (KeyError, TypeError, ValueError, ValidationError, json.JSONDecodeError):
        logger.warning("Skipping malformed stored case %s during read.", row["case_id"])
        return None


def _parse_analysis_snapshot(value: str | None) -> CompleteAnalyzeResponse | None:
    """Read compatible snapshots from older API versions without changing their case summary."""
    if not value:
        return None
    try:
        snapshot = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(snapshot, dict):
        return None

    # Always derive risk level from the final stored numerical score. Older
    # snapshots may contain levels created under previous threshold schemes.
    score = snapshot.get("risk_score")
    if isinstance(score, int) and not isinstance(score, bool):
        snapshot["risk_level"] = get_risk_level(score)

    # Earlier no-AI snapshots stored 0 as a placeholder. Replace it with a
    # deterministic evidence-based estimate, never an invented AI value.
    ai_result = snapshot.get("ai_analysis", {}).get("result") if isinstance(snapshot.get("ai_analysis"), dict) else None
    if not ai_result:
        indicators = [Indicator.model_validate(item) for item in snapshot.get("indicators", [])]
        snapshot["confidence"] = calculate_deterministic_confidence(
            snapshot.get("risk_score", 0), snapshot.get("classification", "SUSPICIOUS"), indicators
        )
        snapshot["confidence_source"] = "deterministic_fallback"
    else:
        snapshot.setdefault("confidence_source", "ai_semantic")

    try:
        return CompleteAnalyzeResponse.model_validate(snapshot)
    except ValidationError:
        return None


def _stored_confidence(
    value: int | None,
    analysis: CompleteAnalyzeResponse | None,
    risk_score: int,
    classification: str,
    indicators: list[Indicator],
) -> int:
    """Preserve AI confidence or rebuild no-AI confidence from deterministic evidence."""
    if analysis:
        return analysis.confidence
    if value is not None:
        return value
    return calculate_deterministic_confidence(risk_score, classification, indicators)


def _case_with_analysis(case: CaseCreateRequest) -> CaseCreateRequest:
    """Attach the exact completed analysis when the client stores its matching case."""
    analysis = case.analysis or _RECENT_ANALYSES.get(case.case_id)
    if analysis is None:
        return case

    # Update case_id on analysis copy to match the case being created
    if analysis.case_id != case.case_id:
        analysis = analysis.model_copy(update={"case_id": case.case_id})

    # Ensure risk_level on analysis is strictly derived from get_risk_level(analysis.risk_score)
    final_score = analysis.risk_score
    final_level = get_risk_level(final_score)
    if analysis.risk_level != final_level:
        analysis = analysis.model_copy(update={"risk_level": final_level})

    return case.model_copy(
        update={
            "risk_score": final_score,
            "classification": analysis.classification,
            "confidence": analysis.confidence,
            "indicators": analysis.indicators,
            "analysis": analysis,
        }
    )



def _migrate_nullable_confidence(connection: sqlite3.Connection) -> None:
    """Make legacy confidence storage nullable without losing stored cases."""
    connection.execute(
        """
        CREATE TABLE cases_migrated (
            case_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            filename TEXT NOT NULL,
            risk_score INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
            classification TEXT NOT NULL,
            confidence INTEGER CHECK (confidence BETWEEN 0 AND 100),
            summary TEXT NOT NULL,
            indicators_json TEXT NOT NULL,
            analysis_json TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO cases_migrated
        SELECT case_id, timestamp, filename, risk_score, classification,
               confidence, summary, indicators_json, analysis_json
        FROM cases
        """
    )
    connection.execute("DROP TABLE cases")
    connection.execute("ALTER TABLE cases_migrated RENAME TO cases")
