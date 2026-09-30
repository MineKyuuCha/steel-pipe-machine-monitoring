"""
database.py
-----------
PostgreSQL data layer for the Steel Pipe Production Monitoring System.
(Migrated from SQLite -- same table shape, same function names, so
receiver.py and app.py don't need to change at all.)

Connection settings come from environment variables, loaded from a
local .env file (see .env.example) -- this keeps your DB password out
of the code that gets pushed to GitHub.
"""

import os
from datetime import datetime, date

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()  # reads a .env file in this folder, if one exists

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "steel_pipe_db") #steel_pipe_db is my server name at
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Change/add machine names here if want add more machines later.
MACHINES = ["A", "B"]


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_db():
    """Create the table if it doesn't exist yet. Safe to call every run."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS machine_events (
            id SERIAL PRIMARY KEY,
            machine_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('ON', 'OFF')),
            timestamp TIMESTAMP NOT NULL
        )
        """
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_machine_time ON machine_events (machine_name, timestamp)"
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_event(machine_name: str, status: str, timestamp: datetime = None):
    """
    Log a state change. This is the ONE function the Flask receiver
    (fed by the ESP32) calls every time a machine turns ON or OFF.
    """
    timestamp = timestamp or datetime.now()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO machine_events (machine_name, status, timestamp) VALUES (%s, %s, %s)",
        (machine_name, status, timestamp),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_latest_status(machine_name: str):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """SELECT * FROM machine_events
           WHERE machine_name = %s
           ORDER BY timestamp DESC LIMIT 1""",
        (machine_name,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_events_for_day(machine_name: str, day: date = None):
    day = day or date.today()
    start = datetime.combine(day, datetime.min.time())
    end = datetime.combine(day, datetime.max.time())
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """SELECT * FROM machine_events
           WHERE machine_name = %s AND timestamp BETWEEN %s AND %s
           ORDER BY timestamp ASC""",
        (machine_name, start, end),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_last_event_before(machine_name: str, timestamp):
    """Used to know what state a machine was already in at midnight."""
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """SELECT * FROM machine_events
           WHERE machine_name = %s AND timestamp < %s
           ORDER BY timestamp DESC LIMIT 1""",
        (machine_name, timestamp),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_recent_events(limit: int = 10):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM machine_events ORDER BY timestamp DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def format_duration(seconds):
    """Turn seconds into hh:mm:ss for display."""
    if seconds is None:
        return "-"
    seconds = int(max(seconds, 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def compute_today_stats(machine_name: str, day: date = None):
    """
    Turns raw ON/OFF event rows into everything the dashboard needs:
    current status, running time, total ON/OFF seconds today,
    utilization %, first ON time, and a timeline for the chart.
    """
    day = day or date.today()
    now = datetime.now()
    day_start = datetime.combine(day, datetime.min.time())
    day_end = min(datetime.combine(day, datetime.max.time()), now)

    events = get_events_for_day(machine_name, day)

    # What state was the machine already in at midnight?
    prev = get_last_event_before(machine_name, day_start)
    state = prev["status"] if prev else "OFF"

    cursor_time = day_start
    total_on_seconds = 0.0
    first_on = None
    timeline = [(day_start, state)]  # (timestamp, status) pairs for charting

    for ev in events:
        ev_time = ev["timestamp"]  # already a real datetime, no parsing needed
        if state == "ON":
            total_on_seconds += (ev_time - cursor_time).total_seconds()
        state = ev["status"]
        if state == "ON" and first_on is None:
            first_on = ev_time
        cursor_time = ev_time
        timeline.append((ev_time, state))

    if state == "ON":
        total_on_seconds += (day_end - cursor_time).total_seconds()
    timeline.append((day_end, state))

    total_elapsed = (day_end - day_start).total_seconds()
    total_off_seconds = max(total_elapsed - total_on_seconds, 0)
    utilization_pct = (total_on_seconds / total_elapsed * 100) if total_elapsed > 0 else 0.0

    latest = get_latest_status(machine_name)
    since = None
    running_seconds = None
    if latest:
        since = latest["timestamp"]
        running_seconds = (now - since).total_seconds()

    return {
        "machine_name": machine_name,
        "current_status": latest["status"] if latest else "OFF",
        "since": since,
        "running_seconds": running_seconds,
        "total_on_seconds": total_on_seconds,
        "total_off_seconds": total_off_seconds,
        "utilization_pct": utilization_pct,
        "first_on": first_on,
        "timeline": timeline,
    }
