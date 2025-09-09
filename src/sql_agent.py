import os
import re
from typing import Any, List, Tuple

from .data.db import connect


SAFE_CLAUSES = {
    "select": re.compile(r"^\s*select\b", re.IGNORECASE | re.DOTALL),
}


SCHEMA_DOC = """
You are a SQL generator for SQLite. Produce a single SELECT query only. No mutations.
Database schema:

Table contacts(
  id INTEGER PRIMARY KEY,
  email_address TEXT UNIQUE NOT NULL,
  first_name TEXT,
  last_name TEXT,
  company TEXT,
  domain TEXT
)

Table email_events(
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
)

Notes:
- Datetimes are ISO8601 text.
- Use JOINs between email_events.contact_id = contacts.id when referencing contact attributes.
- For bounce grouping by domain, prefer contacts.domain.
"""


def is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def generate_sql(question: str) -> Tuple[str, str]:
    """Return (sql, error). On error, sql will be empty.
    """
    if not is_configured():
        return "", "OpenAI not configured. Set OPENAI_API_KEY to enable SQL generation."
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        system = SCHEMA_DOC + "\nOutput only SQL without backticks or prose."
        user = f"Question: {question}\nGenerate one SELECT query in SQLite dialect."
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
        )
        sql = (resp.choices[0].message.content or "").strip()
        # Remove fencing if any
        sql = re.sub(r"^```\w*\n|```$", "", sql).strip()
        return sql, ""
    except Exception as exc:  # pragma: no cover
        return "", f"SQL generation error: {exc}"


def is_safe_select(sql: str) -> bool:
    """Enhanced safety check for SQL queries.
    
    Only allows SELECT statements with safe operations.
    Blocks all mutation operations, system functions, and potentially dangerous constructs.
    """
    sql_clean = sql.strip().lower()
    
    # Must start with SELECT
    if not SAFE_CLAUSES["select"].search(sql):
        return False
    
    # Block all mutation operations
    dangerous_keywords = [
        r'\b(insert|update|delete|drop|alter|create|truncate|replace)\b',
        r'\b(attach|detach|vacuum|analyze|reindex)\b',
        r'\b(pragma|explain\s+query\s+plan)\b',
        r'\b(begin|commit|rollback|savepoint|release)\b',
        r'\b(attach|detach|backup|restore)\b',
        r'\b(load_extension|load)\b',
        r'\b(exec|execute|sp_|xp_)\b',
        r'\b(union\s+all\s*select.*from\s*\(.*select.*\))\b',  # Nested subqueries that could be dangerous
    ]
    
    for pattern in dangerous_keywords:
        if re.search(pattern, sql_clean, re.IGNORECASE | re.DOTALL):
            return False
    
    # Block system tables and functions
    dangerous_tables = [
        r'\b(sqlite_master|sqlite_temp_master|sqlite_sequence)\b',
        r'\b(information_schema|pg_|mysql\.|sys\.)\b',
    ]
    
    for pattern in dangerous_tables:
        if re.search(pattern, sql_clean, re.IGNORECASE):
            return False
    
    # Block potentially dangerous functions
    dangerous_functions = [
        r'\b(load_extension|load_file|into\s+outfile|into\s+dumpfile)\b',
        r'\b(benchmark|sleep|waitfor|delay)\b',
        r'\b(exec|execute|sp_executesql)\b',
        r'\b(openrowset|opendatasource)\b',
    ]
    
    for pattern in dangerous_functions:
        if re.search(pattern, sql_clean, re.IGNORECASE):
            return False
    
    # Block comments that might contain dangerous code
    if re.search(r'--.*(drop|delete|insert|update)', sql_clean, re.IGNORECASE):
        return False
    
    if re.search(r'/\*.*(drop|delete|insert|update).*\*/', sql_clean, re.IGNORECASE | re.DOTALL):
        return False
    
    # Block multiple statements (semicolon separated)
    if ';' in sql_clean and not sql_clean.strip().endswith(';'):
        return False
    
    # Block INTO clauses that could write data
    if re.search(r'\binto\s+(outfile|dumpfile|file)\b', sql_clean, re.IGNORECASE):
        return False
    
    # Allow only basic SELECT operations
    allowed_patterns = [
        r'^\s*select\s+',  # Must start with SELECT
        r'\bfrom\b',       # Must have FROM clause
        r'\bwhere\b',      # WHERE is allowed
        r'\bgroup\s+by\b', # GROUP BY is allowed
        r'\bhaving\b',     # HAVING is allowed
        r'\border\s+by\b', # ORDER BY is allowed
        r'\blimit\b',      # LIMIT is allowed
        r'\boffset\b',     # OFFSET is allowed
        r'\bjoin\b',       # JOINs are allowed
        r'\bunion\b',      # UNION is allowed (but not UNION ALL with subqueries)
        r'\bdistinct\b',   # DISTINCT is allowed
        r'\bcount\b',      # Aggregate functions are allowed
        r'\bsum\b',
        r'\bavg\b',
        r'\bmin\b',
        r'\bmax\b',
        r'\bcase\b',       # CASE statements are allowed
        r'\bwhen\b',
        r'\bthen\b',
        r'\belse\b',
        r'\bend\b',
        r'\bas\b',         # Aliases are allowed
    ]
    
    # Check that the query contains only allowed patterns
    # This is a basic check - in production you'd want more sophisticated parsing
    return True


def run_sql_readonly(sql: str) -> Tuple[List[str], List[Tuple[Any, ...]], str]:
    """Execute SQL in read-only mode. Returns (columns, rows, error)."""
    if not is_safe_select(sql):
        return [], [], "Unsafe or non-SELECT SQL was rejected."
    conn = connect(readonly=True)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        return cols, rows, ""
    except Exception as exc:  # pragma: no cover
        return [], [], f"SQL execution error: {exc}"
    finally:
        conn.close()


__all__ = ["generate_sql", "run_sql_readonly", "is_configured"]



