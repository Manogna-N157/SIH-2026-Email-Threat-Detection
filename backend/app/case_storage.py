"""Minimal SQLite persistence for completed email-analysis cases."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

from pydantic import ValidationError

from app.confidence_engine import calculate_deterministic_confidence
from app.risk_engine import get_risk_level
from app.schemas import CaseCreateRequest, CompleteAnalyzeResponse, Indicator, StoredCase


DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "cases.db"
logger = logging.getLogger(__name__)


class CaseAlreadyExistsError(Exception):
    """Raised when a caller tries to reuse an existing case ID."""


def create_case(case: CaseCreateRequest) -> StoredCase:
    _initialize_database()
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
                    case.case_id,
                    case.timestamp.isoformat(),
                    case.filename,
                    case.risk_score,
                    case.classification,
                    case.confidence,
                    case.summary,
                    json.dumps([indicator.model_dump() for indicator in case.indicators]),
                    case.analysis.model_dump_json() if case.analysis else None,
                ),
            )
    except sqlite3.IntegrityError as exc:
        raise CaseAlreadyExistsError(case.case_id) from exc
    return StoredCase(**case.model_dump())


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

    # `risk_level` was introduced after earlier case snapshots were persisted.
    score = snapshot.get("risk_score")
    if isinstance(score, int) and not isinstance(score, bool):
        snapshot.setdefault("risk_level", get_risk_level(score))

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
