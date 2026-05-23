"""
ARIA Database Layer — database.py (MySQL edition)
Drop this into your aria-agent/ folder alongside main.py.

Install driver:
    pip install mysql-connector-python

Add to your .env:
    MYSQL_HOST=localhost
    MYSQL_PORT=3306
    MYSQL_USER=root
    MYSQL_PASSWORD=your_password
    MYSQL_DATABASE=aria
"""

import json
import os
from datetime import date
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Connection pool — reuses connections instead of opening a
# new one on every query (important for a long-running bot)
# ─────────────────────────────────────────────────────────────
_pool = pooling.MySQLConnectionPool(
    pool_name="aria_pool",
    pool_size=5,
    host=os.getenv("MYSQL_HOST", "localhost"),
    port=int(os.getenv("MYSQL_PORT", 3306)),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "aria"),
    autocommit=False,
)


@contextmanager
def get_conn():
    """Yield a connection from the pool, commit on success, rollback on error."""
    conn = _pool.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()  # returns to pool, doesn't actually close TCP


# ─────────────────────────────────────────────────────────────
# Schema — run once at startup
# ─────────────────────────────────────────────────────────────
_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        telegram_id         BIGINT          PRIMARY KEY,
        username            VARCHAR(64),
        first_name          VARCHAR(64),
        timezone            VARCHAR(64)     NOT NULL DEFAULT 'Asia/Kolkata',
        wake_time           VARCHAR(5),                 -- 'HH:MM'
        sleep_time          VARCHAR(5),                 -- 'HH:MM'
        sleep_goal_hours    FLOAT,
        task_reminder_gap   INT             NOT NULL DEFAULT 90,
        onboarded           TINYINT(1)      NOT NULL DEFAULT 0,
        created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS checkins (
        id                  BIGINT          PRIMARY KEY AUTO_INCREMENT,
        telegram_id         BIGINT          NOT NULL,
        checkin_date        DATE            NOT NULL,
        sleep_time          VARCHAR(32),
        wake_time           VARCHAR(32),
        sleep_hours         FLOAT,
        energy_level        VARCHAR(32),
        tasks               JSON,
        summary_sent        TINYINT(1)      NOT NULL DEFAULT 0,
        created_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_user_date (telegram_id, checkin_date),
        FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS task_completions (
        id                  BIGINT          PRIMARY KEY AUTO_INCREMENT,
        checkin_id          BIGINT          NOT NULL,
        task_index          INT             NOT NULL,
        task_text           VARCHAR(512)    NOT NULL,
        completed           TINYINT(1)      NOT NULL DEFAULT 0,
        completed_at        DATETIME,
        UNIQUE KEY uq_checkin_task (checkin_id, task_index),
        FOREIGN KEY (checkin_id) REFERENCES checkins(id)
    )
    """,
]


def init_db() -> None:
    """Create tables if they don't exist. Call once at bot startup."""
    with get_conn() as conn:
        cursor = conn.cursor()
        for stmt in _SCHEMA:
            cursor.execute(stmt)
        cursor.close()
    print("[ARIA DB] MySQL tables ready.")


# ─────────────────────────────────────────────────────────────
# User helpers
# ─────────────────────────────────────────────────────────────

def upsert_user(telegram_id: int, username: str | None, first_name: str | None) -> None:
    sql = """
        INSERT INTO users (telegram_id, username, first_name)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            username   = VALUES(username),
            first_name = VALUES(first_name)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (telegram_id, username, first_name))
        cur.close()


def get_user(telegram_id: int) -> dict | None:
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
        row = cur.fetchone()
        cur.close()
    return row


def save_user_prefs(
    telegram_id: int,
    wake_time: str | None = None,
    sleep_time: str | None = None,
    sleep_goal_hours: float | None = None,
    task_reminder_gap: int | None = None,
    task_limit: int | None = None,
    onboarded: bool | None = None,
) -> None:
    """Update only the fields you pass — None fields are left untouched."""
    fields, values = [], []
    if wake_time          is not None: fields.append("wake_time = %s");          values.append(wake_time)
    if sleep_time         is not None: fields.append("sleep_time = %s");         values.append(sleep_time)
    if sleep_goal_hours   is not None: fields.append("sleep_goal_hours = %s");   values.append(sleep_goal_hours)
    if task_reminder_gap  is not None: fields.append("task_reminder_gap = %s");  values.append(task_reminder_gap)
    if task_limit         is not None: fields.append("task_limit = %s");         values.append(task_limit)
    if onboarded          is not None: fields.append("onboarded = %s");           values.append(int(onboarded))
    if not fields:
        return
    values.append(telegram_id)
    sql = f"UPDATE users SET {', '.join(fields)} WHERE telegram_id = %s"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, values)
        cur.close()


def get_all_onboarded_users() -> list[dict]:
    """Return all users who completed onboarding — used to restore alarms on restart."""
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE onboarded = 1")
        rows = cur.fetchall()
        cur.close()
    return rows


# ─────────────────────────────────────────────────────────────
# Check-in helpers
# ─────────────────────────────────────────────────────────────

def save_checkin(
    telegram_id: int,
    sleep_time: str | None = None,
    wake_time: str | None = None,
    sleep_hours: float | None = None,
    energy_level: str | None = None,
    tasks: list[str] | None = None,
    checkin_date: str | None = None,
) -> int:
    """
    Upsert today's check-in. Partial saves are fine — call incrementally
    as each answer arrives. Returns the checkin row id.
    """
    today = checkin_date or date.today().isoformat()
    tasks_json = json.dumps(tasks) if tasks is not None else None

    sql = """
        INSERT INTO checkins
            (telegram_id, checkin_date, sleep_time, wake_time, sleep_hours, energy_level, tasks)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sleep_time    = COALESCE(VALUES(sleep_time),    sleep_time),
            wake_time     = COALESCE(VALUES(wake_time),     wake_time),
            sleep_hours   = COALESCE(VALUES(sleep_hours),   sleep_hours),
            energy_level  = COALESCE(VALUES(energy_level),  energy_level),
            tasks         = COALESCE(VALUES(tasks),          tasks)
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (telegram_id, today, sleep_time, wake_time,
                          sleep_hours, energy_level, tasks_json))
        # Get the id whether it was an INSERT or UPDATE
        cur.execute(
            "SELECT id FROM checkins WHERE telegram_id = %s AND checkin_date = %s",
            (telegram_id, today),
        )
        checkin_id = cur.fetchone()[0]

        if tasks is not None:
            _sync_task_completions(conn, checkin_id, tasks)

        cur.close()
    return checkin_id


def get_todays_checkin(telegram_id: int, checkin_date: str | None = None) -> dict | None:
    today = checkin_date or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM checkins WHERE telegram_id = %s AND checkin_date = %s",
            (telegram_id, today),
        )
        row = cur.fetchone()
        cur.close()
    if row and row.get("tasks"):
        row["tasks"] = json.loads(row["tasks"]) if isinstance(row["tasks"], str) else row["tasks"]
    return row


def get_checkin_history(telegram_id: int, limit: int = 7) -> list[dict]:
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT * FROM checkins
            WHERE telegram_id = %s
            ORDER BY checkin_date DESC
            LIMIT %s
            """,
            (telegram_id, limit),
        )
        rows = cur.fetchall()
        cur.close()
    for r in rows:
        if r.get("tasks"):
            r["tasks"] = json.loads(r["tasks"]) if isinstance(r["tasks"], str) else r["tasks"]
    return rows


# ─────────────────────────────────────────────────────────────
# Task-completion helpers
# ─────────────────────────────────────────────────────────────

def _sync_task_completions(conn, checkin_id: int, tasks: list[str]) -> None:
    cur = conn.cursor()
    for idx, text in enumerate(tasks):
        cur.execute(
            """
            INSERT INTO task_completions (checkin_id, task_index, task_text)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE task_text = VALUES(task_text)
            """,
            (checkin_id, idx, text),
        )
    cur.close()


def mark_task_done(telegram_id: int, task_index: int, checkin_date: str | None = None) -> bool:
    today = checkin_date or date.today().isoformat()
    sql = """
        UPDATE task_completions tc
        JOIN checkins c ON c.id = tc.checkin_id
        SET tc.completed = 1, tc.completed_at = NOW()
        WHERE c.telegram_id = %s
          AND c.checkin_date = %s
          AND tc.task_index = %s
          AND tc.completed = 0
    """
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, (telegram_id, today, task_index))
        updated = cur.rowcount > 0
        cur.close()
    return updated


def get_task_completions(telegram_id: int, checkin_date: str | None = None) -> list[dict]:
    today = checkin_date or date.today().isoformat()
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT tc.*
            FROM task_completions tc
            JOIN checkins c ON c.id = tc.checkin_id
            WHERE c.telegram_id = %s AND c.checkin_date = %s
            ORDER BY tc.task_index
            """,
            (telegram_id, today),
        )
        rows = cur.fetchall()
        cur.close()
    return rows


# ─────────────────────────────────────────────────────────────
# Analytics (seeds for ML layer later)
# ─────────────────────────────────────────────────────────────

def get_avg_energy_numeric(telegram_id: int, days: int = 7) -> dict:
    """Returns counts of High/Medium/Low over last N days."""
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT energy_level, COUNT(*) AS cnt
            FROM checkins
            WHERE telegram_id = %s
              AND energy_level IS NOT NULL
              AND checkin_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY energy_level
            """,
            (telegram_id, days),
        )
        rows = cur.fetchall()
        cur.close()
    return {r["energy_level"]: r["cnt"] for r in rows}


def get_completion_rate(telegram_id: int, days: int = 7) -> float | None:
    with get_conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
                COUNT(*)        AS total,
                SUM(tc.completed) AS done
            FROM task_completions tc
            JOIN checkins c ON c.id = tc.checkin_id
            WHERE c.telegram_id = %s
              AND c.checkin_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            """,
            (telegram_id, days),
        )
        row = cur.fetchone()
        cur.close()
    if row and row["total"]:
        return row["done"] / row["total"]
    return None
