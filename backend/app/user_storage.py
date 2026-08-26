"""Minimal SQLite persistence and authentication for users and roles."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "cases.db"
logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    """Hash password securely using SHA-256 with salt."""
    salt = "sih_2026_forensics_salt_v1"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


def initialize_user_database() -> None:
    """Ensure users table exists and seed initial default admin user if missing."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('ADMIN', 'USER')),
                status TEXT NOT NULL CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

        # Seed initial admin account if no admin exists
        cursor = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'ADMIN'")
        admin_count = cursor.fetchone()[0]
        if admin_count == 0:
            admin_id = str(uuid.uuid4())
            admin_pw_hash = _hash_password("admin123")
            created_at = datetime.now(timezone.utc).isoformat()
            try:
                conn.execute(
                    """
                    INSERT INTO users (id, username, email, password_hash, role, status, created_at)
                    VALUES (?, ?, ?, ?, 'ADMIN', 'APPROVED', ?)
                    """,
                    (admin_id, "admin", "admin@sih.gov.in", admin_pw_hash, created_at),
                )
                conn.commit()
                logger.info("Seeded initial default admin account.")
            except sqlite3.IntegrityError:
                pass


def register_user(username: str, email: str, password: str) -> dict:
    """Register a new user with status PENDING and role USER."""
    initialize_user_database()
    username_clean = username.strip().lower()
    email_clean = email.strip().lower()
    user_id = str(uuid.uuid4())
    pw_hash = _hash_password(password)
    created_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_PATH) as conn:
        # Check uniqueness
        cursor = conn.execute("SELECT username, email FROM users WHERE username = ? OR email = ?", (username_clean, email_clean))
        existing = cursor.fetchone()
        if existing:
            if existing[0] == username_clean:
                raise ValueError("Username is already taken.")
            raise ValueError("Email is already registered.")

        conn.execute(
            """
            INSERT INTO users (id, username, email, password_hash, role, status, created_at)
            VALUES (?, ?, ?, ?, 'USER', 'PENDING', ?)
            """,
            (user_id, username_clean, email_clean, pw_hash, created_at),
        )
        conn.commit()

    return {
        "id": user_id,
        "username": username_clean,
        "email": email_clean,
        "role": "USER",
        "status": "PENDING",
        "created_at": created_at,
    }


def authenticate_user(username_or_email: str, password: str) -> dict:
    """Authenticate user credentials and verify registration status."""
    initialize_user_database()
    identifier = username_or_email.strip().lower()
    pw_hash = _hash_password(password)

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT id, username, email, password_hash, role, status, created_at FROM users WHERE username = ? OR email = ?",
            (identifier, identifier),
        )
        user = cursor.fetchone()

        if not user or user["password_hash"] != pw_hash:
            raise PermissionError("Invalid username or password.")

        if user["status"] == "PENDING":
            raise ValueError("Your account is pending administrator approval.")

        if user["status"] == "REJECTED":
            raise ValueError("Your account registration has been rejected by an administrator.")

        token = f"token_{user['id']}_{user['role']}"
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "status": user["status"],
            "created_at": user["created_at"],
            "token": token,
        }


def list_users() -> list[dict]:
    """List all registered users for admin review."""
    initialize_user_database()
    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT id, username, email, role, status, created_at FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_user_status(user_id: str, new_status: str) -> dict:
    """Approve or reject a user account."""
    initialize_user_database()
    if new_status not in ("APPROVED", "REJECTED", "PENDING"):
        raise ValueError("Invalid status value.")

    with sqlite3.connect(DATABASE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        if cursor.rowcount == 0:
            raise KeyError("User not found.")
        conn.commit()

        cursor = conn.execute("SELECT id, username, email, role, status, created_at FROM users WHERE id = ?", (user_id,))
        return dict(cursor.fetchone())


def delete_user(user_id: str) -> bool:
    """Delete a user account."""
    initialize_user_database()
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cursor.rowcount > 0
