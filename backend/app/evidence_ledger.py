"""Small append-only SHA-256 evidence ledger for stored forensic cases."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.risk_engine import get_risk_level
from app.schemas import EvidenceBlock, StoredCase


GENESIS_HASH = "GENESIS"


def initialize_ledger(connection: sqlite3.Connection) -> None:
    """Create the ledger in the application's existing SQLite database."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS evidence_blocks (
            block_index INTEGER PRIMARY KEY,
            case_id TEXT NOT NULL UNIQUE,
            evidence_hash TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            current_hash TEXT NOT NULL UNIQUE
        )
        """
    )


def build_evidence(case: StoredCase) -> dict[str, Any]:
    """Build minimal deterministic case evidence without including secrets or raw bodies."""
    analysis = case.analysis
    email = analysis.email if analysis else None
    ai_result = analysis.ai_analysis.result if analysis else None

    return {
        "case_id": case.case_id,
        "timestamp": case.timestamp.isoformat(),
        "risk_score": case.risk_score,
        "risk_level": get_risk_level(case.risk_score),
        "classification": case.classification,
        "confidence": case.confidence,
        "sender": _addresses(email.from_ if email else []),
        "recipients": _addresses(email.to if email else []),
        "ips": analysis.ips if analysis else [],
        "urls": analysis.urls if analysis else [],
        "infrastructure": _infrastructure(analysis.ip_intelligence if analysis else []),
        "ai_analysis": ai_result.model_dump(mode="json") if ai_result else None,
    }


def evidence_hash(case: StoredCase) -> str:
    return _sha256(_canonical_json(build_evidence(case)))


def append_block(connection: sqlite3.Connection, case: StoredCase) -> EvidenceBlock:
    """Append one block after a case is stored; caller owns the transaction."""
    previous = connection.execute(
        "SELECT block_index, current_hash FROM evidence_blocks ORDER BY block_index DESC LIMIT 1"
    ).fetchone()
    index = (previous["block_index"] + 1) if previous else 0
    previous_hash = previous["current_hash"] if previous else GENESIS_HASH
    timestamp = datetime.now(timezone.utc)
    calculated_evidence_hash = evidence_hash(case)
    current_hash = calculate_block_hash(
        index=index,
        case_id=case.case_id,
        evidence_hash_value=calculated_evidence_hash,
        timestamp=timestamp,
        previous_hash=previous_hash,
    )
    block = EvidenceBlock(
        index=index,
        case_id=case.case_id,
        evidence_hash=calculated_evidence_hash,
        timestamp=timestamp,
        previous_hash=previous_hash,
        current_hash=current_hash,
    )
    connection.execute(
        """
        INSERT INTO evidence_blocks (
            block_index, case_id, evidence_hash, timestamp, previous_hash, current_hash
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            block.index,
            block.case_id,
            block.evidence_hash,
            block.timestamp.isoformat(),
            block.previous_hash,
            block.current_hash,
        ),
    )
    return block


def calculate_block_hash(
    *,
    index: int,
    case_id: str,
    evidence_hash_value: str,
    timestamp: datetime,
    previous_hash: str,
) -> str:
    """Hash exactly the immutable block contents, including chain linkage."""
    return _sha256(
        _canonical_json(
            {
                "index": index,
                "case_id": case_id,
                "evidence_hash": evidence_hash_value,
                "timestamp": timestamp.isoformat(),
                "previous_hash": previous_hash,
            }
        )
    )


def list_blocks(connection: sqlite3.Connection) -> list[EvidenceBlock]:
    rows = connection.execute(
        "SELECT block_index, case_id, evidence_hash, timestamp, previous_hash, current_hash "
        "FROM evidence_blocks ORDER BY block_index ASC"
    ).fetchall()
    return [_row_to_block(row) for row in rows]


def get_block(connection: sqlite3.Connection, case_id: str) -> EvidenceBlock | None:
    row = connection.execute(
        "SELECT block_index, case_id, evidence_hash, timestamp, previous_hash, current_hash "
        "FROM evidence_blocks WHERE case_id = ?",
        (case_id,),
    ).fetchone()
    return _row_to_block(row) if row else None


def verify_block_chain(connection: sqlite3.Connection, block: EvidenceBlock) -> bool:
    """Verify block hashes and linkage from GENESIS through the requested block."""
    blocks = connection.execute(
        "SELECT block_index, case_id, evidence_hash, timestamp, previous_hash, current_hash "
        "FROM evidence_blocks WHERE block_index <= ? ORDER BY block_index ASC",
        (block.index,),
    ).fetchall()
    if len(blocks) != block.index + 1:
        return False

    expected_previous_hash = GENESIS_HASH
    for row in blocks:
        candidate = _row_to_block(row)
        if candidate.previous_hash != expected_previous_hash:
            return False
        if candidate.current_hash != calculate_block_hash(
            index=candidate.index,
            case_id=candidate.case_id,
            evidence_hash_value=candidate.evidence_hash,
            timestamp=candidate.timestamp,
            previous_hash=candidate.previous_hash,
        ):
            return False
        expected_previous_hash = candidate.current_hash
    return True


def _addresses(addresses: list[Any]) -> list[dict[str, str | None]]:
    return [
        {"display_name": address.display_name, "address": address.address, "domain": address.domain}
        for address in addresses
    ]


def _infrastructure(intelligence: list[Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in intelligence:
        location = item.probable_infrastructure_location
        evidence.append(
            {
                "ip": item.ip,
                "source": item.source,
                "address_class": item.address_class,
                "location": location.model_dump(mode="json") if location else None,
            }
        )
    return evidence


def _canonical_json(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _row_to_block(row: sqlite3.Row) -> EvidenceBlock:
    return EvidenceBlock(
        index=row["block_index"],
        case_id=row["case_id"],
        evidence_hash=row["evidence_hash"],
        timestamp=row["timestamp"],
        previous_hash=row["previous_hash"],
        current_hash=row["current_hash"],
    )
