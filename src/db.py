import os
import sqlite3
from typing import Optional, Tuple


DB_FILENAME = "email_campaign.db"


def get_db_path() -> str:
    """Return absolute path to the SQLite database file."""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), DB_FILENAME)


def connect(readonly: bool = False) -> sqlite3.Connection:
    """Create a SQLite connection.

    If readonly is True, opens the database file in read-only mode.
    """
    db_path = get_db_path()
    if readonly:
        # SQLite readonly URI
        uri = f"file:{db_path}?mode=ro"
        return sqlite3.connect(uri, uri=True)
    return sqlite3.connect(db_path)


def init_schema(conn: Optional[sqlite3.Connection] = None) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
    """Create the schema if it does not exist.

    Returns the connection and a cursor with the schema applied.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        close_conn = True

    cur = conn.cursor()
    # Contacts table for joins
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY,
            email_address TEXT UNIQUE NOT NULL,
            first_name TEXT,
            last_name TEXT,
            company TEXT,
            domain TEXT
        );
        """
    )
    # Events table (may already exist from earlier runs)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS email_events (
            id INTEGER PRIMARY KEY,
            email_address TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            company TEXT,
            subject TEXT,
            campaign_name TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            delivered_at TEXT,
            opened_at TEXT,
            replied_at TEXT,
            bounced INTEGER NOT NULL DEFAULT 0,
            contact_id INTEGER
        );
        """
    )
    # Backfill: add contact_id if missing (SQLite has no IF NOT EXISTS for columns)
    cur.execute("PRAGMA table_info(email_events)")
    cols = [r[1] for r in cur.fetchall()]
    if "contact_id" not in cols:
        try:
            cur.execute("ALTER TABLE email_events ADD COLUMN contact_id INTEGER")
        except sqlite3.OperationalError:
            pass
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_email_domain ON email_events (email_address);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_campaign_sent ON email_events (campaign_name, sent_at);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts (email_address);
        """
    )
    conn.commit()

    if close_conn:
        return conn, cur
    return conn, cur


__all__ = ["connect", "init_schema", "get_db_path", "DB_FILENAME"]


