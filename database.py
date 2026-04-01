"""
Database layer for LuxNumbers Bot — SQLite
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from config import TRIAL_DAYS


class Database:
    def __init__(self, path: str = "luxbot.db"):
        self.path = path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    joined_at   TEXT DEFAULT (datetime('now')),
                    trial_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS whitelist (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT,
                    note        TEXT,
                    added_at    TEXT DEFAULT (datetime('now')),
                    is_active   INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS numbers (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    number      TEXT UNIQUE NOT NULL,
                    label       TEXT DEFAULT 'Collectible',
                    assigned_to INTEGER,
                    assigned_at TEXT,
                    expires_at  TEXT,
                    is_active   INTEGER DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS trial_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    number      TEXT NOT NULL,
                    started_at  TEXT DEFAULT (datetime('now')),
                    expired_at  TEXT,
                    status      TEXT DEFAULT 'active'
                );
            """)

    # ── WHITELIST ─────────────────────────────────────────────────────────────

    def is_whitelisted(self, user_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT is_active FROM whitelist WHERE user_id = ?", (user_id,)
            ).fetchone()
            return bool(row and row["is_active"])

    def add_to_whitelist(self, user_id: int, username: str = "", note: str = ""):
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO whitelist (user_id, username, note)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET is_active=1, username=excluded.username, note=excluded.note""",
                (user_id, username, note)
            )

    def remove_from_whitelist(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE whitelist SET is_active = 0 WHERE user_id = ?", (user_id,)
            )

    def list_whitelist(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, username, note, added_at, is_active FROM whitelist ORDER BY added_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    # ── USERS ────────────────────────────────────────────────────────────────

    def ensure_user(self, user_id: int, username: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                (user_id, username)
            )
            conn.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (username, user_id)
            )

    def has_used_trial(self, user_id: int) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT trial_count FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            return row and row["trial_count"] > 0

    def list_all_users(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT u.user_id, u.username, u.joined_at, u.trial_count,
                          w.is_active as whitelisted
                   FROM users u
                   LEFT JOIN whitelist w ON u.user_id = w.user_id
                   ORDER BY u.joined_at DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    # ── NUMBERS ──────────────────────────────────────────────────────────────

    def add_number(self, number: str, label: str = "Collectible"):
        with self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO numbers (number, label) VALUES (?, ?)",
                (number, label)
            )

    def remove_number(self, number_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE numbers SET is_active = 0, assigned_to = NULL, expires_at = NULL WHERE id = ?",
                (number_id,)
            )

    def toggle_number(self, number_id: int, active: bool):
        with self._conn() as conn:
            conn.execute(
                "UPDATE numbers SET is_active = ? WHERE id = ?",
                (1 if active else 0, number_id)
            )

    def assign_number(self, user_id: int) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT id, number FROM numbers
                   WHERE assigned_to IS NULL AND is_active = 1
                   ORDER BY RANDOM() LIMIT 1"""
            ).fetchone()
            if not row:
                return None
            expires_at = (datetime.utcnow() + timedelta(days=TRIAL_DAYS)).isoformat()
            conn.execute(
                """UPDATE numbers
                   SET assigned_to = ?, assigned_at = datetime('now'), expires_at = ?
                   WHERE id = ?""",
                (user_id, expires_at, row["id"])
            )
            conn.execute(
                "INSERT INTO trial_history (user_id, number) VALUES (?, ?)",
                (user_id, row["number"])
            )
            conn.execute(
                "UPDATE users SET trial_count = trial_count + 1 WHERE user_id = ?",
                (user_id,)
            )
            return row["number"]

    def get_active_trial(self, user_id: int) -> Optional[Dict]:
        with self._conn() as conn:
            row = conn.execute(
                """SELECT number, expires_at FROM numbers
                   WHERE assigned_to = ? AND expires_at > datetime('now')""",
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def expire_trial(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                """UPDATE numbers
                   SET assigned_to = NULL, assigned_at = NULL, expires_at = NULL
                   WHERE assigned_to = ?""",
                (user_id,)
            )
            conn.execute(
                """UPDATE trial_history SET expired_at = datetime('now'), status = 'expired'
                   WHERE user_id = ? AND status = 'active'""",
                (user_id,)
            )

    def list_all_numbers(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT id, number, label, assigned_to, assigned_at, expires_at, is_active
                   FROM numbers ORDER BY id DESC"""
            ).fetchall()
            return [dict(r) for r in rows]

    # ── STATS ────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        with self._conn() as conn:
            total_users    = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            whitelisted    = conn.execute("SELECT COUNT(*) FROM whitelist WHERE is_active=1").fetchone()[0]
            total_numbers  = conn.execute("SELECT COUNT(*) FROM numbers WHERE is_active=1").fetchone()[0]
            active_trials  = conn.execute(
                "SELECT COUNT(*) FROM numbers WHERE assigned_to IS NOT NULL AND expires_at > datetime('now')"
            ).fetchone()[0]
            available      = conn.execute(
                "SELECT COUNT(*) FROM numbers WHERE assigned_to IS NULL AND is_active=1"
            ).fetchone()[0]
            completed      = conn.execute(
                "SELECT COUNT(*) FROM trial_history WHERE status='expired'"
            ).fetchone()[0]
            return {
                "total_users": total_users,
                "whitelisted": whitelisted,
                "total_numbers": total_numbers,
                "active_trials": active_trials,
                "available_numbers": available,
                "completed_trials": completed,
            }
