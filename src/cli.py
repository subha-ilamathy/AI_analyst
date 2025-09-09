import argparse
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from dateutil import parser as dtparser

try:
    from .data.db import connect
    from .sql_agent import generate_sql, run_sql_readonly, is_configured as sql_is_configured
    from .utils.time_parser import parse_time_simple
    from .utils.response_formatter import format_response_natural, format_error_natural, is_configured as formatter_is_configured
    from .llm import parse_with_llm, is_configured as llm_is_configured
except ImportError:
    # Handle direct execution
    from data.db import connect
    from sql_agent import generate_sql, run_sql_readonly, is_configured as sql_is_configured
    from utils.time_parser import parse_time_simple
    from utils.response_formatter import format_response_natural, format_error_natural, is_configured as formatter_is_configured
    from llm import parse_with_llm, is_configured as llm_is_configured


SUPPORTED_METRICS = {
    "sent",
    "opened",
    "replied",
    "bounced",
}


def extract_time_window_advanced(question: str) -> Tuple[Optional[str], Optional[str]]:
    """Advanced time window extraction using NLP patterns and contextual understanding.
    
    Supports various natural language patterns:
    - Relative periods: "last week", "past 7 days", "this month", "yesterday"
    - Specific dates: "since 2024-01-01", "on 2024-01-15", "from Jan 1 to Jan 31"
    - Date ranges: "between 2024-01-01 and 2024-01-31", "from 2024-01-01 until 2024-01-31"
    - Business periods: "this quarter", "last quarter", "this year", "last year"
    """
    q = question.lower().strip()
    now = datetime.utcnow()
    
    # Helper function to get start of day
    def start_of_day(dt):
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Helper function to get end of day
    def end_of_day(dt):
        return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Pattern 1: Last week (Monday to Sunday)
    if re.search(r'\blast\s+week\b', q):
        today_weekday = now.weekday()  # Monday=0
        start_of_this_week = now - timedelta(days=today_weekday)
        start_of_last_week = start_of_day(start_of_this_week - timedelta(days=7))
        end_of_last_week = end_of_day(start_of_last_week + timedelta(days=6))
        return start_of_last_week.isoformat(), end_of_last_week.isoformat()
    
    # Pattern 2: This week (Monday to now)
    if re.search(r'\bthis\s+week\b', q):
        today_weekday = now.weekday()
        start_of_this_week = start_of_day(now - timedelta(days=today_weekday))
        return start_of_this_week.isoformat(), now.isoformat()
    
    # Pattern 3: Last N days/weeks/months
    days_match = re.search(r'\blast\s+(\d{1,3})\s+days?\b', q)
    if days_match:
        days = int(days_match.group(1))
        start = start_of_day(now - timedelta(days=days))
        return start.isoformat(), now.isoformat()
    
    weeks_match = re.search(r'\blast\s+(\d{1,3})\s+weeks?\b', q)
    if weeks_match:
        weeks = int(weeks_match.group(1))
        start = start_of_day(now - timedelta(weeks=weeks))
        return start.isoformat(), now.isoformat()
    
    months_match = re.search(r'\blast\s+(\d{1,3})\s+months?\b', q)
    if months_match:
        months = int(months_match.group(1))
        # Approximate months as 30 days
        start = start_of_day(now - timedelta(days=months * 30))
        return start.isoformat(), now.isoformat()
    
    # Pattern 4: Past N days/weeks/months
    past_days_match = re.search(r'\bpast\s+(\d{1,3})\s+days?\b', q)
    if past_days_match:
        days = int(past_days_match.group(1))
        start = start_of_day(now - timedelta(days=days))
        return start.isoformat(), now.isoformat()
    
    # Pattern 5: Yesterday
    if re.search(r'\byesterday\b', q):
        yesterday = now - timedelta(days=1)
        start = start_of_day(yesterday)
        end = end_of_day(yesterday)
        return start.isoformat(), end.isoformat()
    
    # Pattern 6: Today
    if re.search(r'\btoday\b', q):
        start = start_of_day(now)
        return start.isoformat(), now.isoformat()
    
    # Pattern 7: This month
    if re.search(r'\bthis\s+month\b', q):
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_of_month.isoformat(), now.isoformat()
    
    # Pattern 8: Last month
    if re.search(r'\blast\s+month\b', q):
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month = first_of_this_month - timedelta(days=1)
        first_of_last_month = last_month.replace(day=1)
        last_day_of_last_month = last_month
        return first_of_last_month.isoformat(), end_of_day(last_day_of_last_month).isoformat()
    
    # Pattern 9: This year
    if re.search(r'\bthis\s+year\b', q):
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_of_year.isoformat(), now.isoformat()
    
    # Pattern 10: Last year
    if re.search(r'\blast\s+year\b', q):
        start_of_this_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        start_of_last_year = start_of_this_year.replace(year=now.year - 1)
        end_of_last_year = start_of_this_year - timedelta(seconds=1)
        return start_of_last_year.isoformat(), end_of_last_year.isoformat()
    
    # Pattern 11: Since specific date (YYYY-MM-DD format)
    since_match = re.search(r'\bsince\s+(\d{4}-\d{2}-\d{2})\b', q)
    if since_match:
        try:
            start = dtparser.parse(since_match.group(1))
            return start.isoformat(), now.isoformat()
        except:
            pass
    
    # Pattern 12: On specific date (YYYY-MM-DD format)
    on_match = re.search(r'\bon\s+(\d{4}-\d{2}-\d{2})\b', q)
    if on_match:
        try:
            date = dtparser.parse(on_match.group(1))
            start = start_of_day(date)
            end = end_of_day(date)
            return start.isoformat(), end.isoformat()
        except:
            pass
    
    # Pattern 13: Between two dates
    between_match = re.search(r'\bbetween\s+(\d{4}-\d{2}-\d{2})\s+and\s+(\d{4}-\d{2}-\d{2})\b', q)
    if between_match:
        try:
            start = dtparser.parse(between_match.group(1))
            end = dtparser.parse(between_match.group(2))
            if end < start:
                return None, None
            return start.isoformat(), end_of_day(end).isoformat()
        except:
            pass
    
    # Pattern 14: From date to date
    from_to_match = re.search(r'\bfrom\s+(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})\b', q)
    if from_to_match:
        try:
            start = dtparser.parse(from_to_match.group(1))
            end = dtparser.parse(from_to_match.group(2))
            if end < start:
                return None, None
            return start.isoformat(), end_of_day(end).isoformat()
        except:
            pass
    
    # Pattern 15: From date until date
    from_until_match = re.search(r'\bfrom\s+(\d{4}-\d{2}-\d{2})\s+until\s+(\d{4}-\d{2}-\d{2})\b', q)
    if from_until_match:
        try:
            start = dtparser.parse(from_until_match.group(1))
            end = dtparser.parse(from_until_match.group(2))
            if end < start:
                return None, None
            return start.isoformat(), end_of_day(end).isoformat()
        except:
            pass
    
    # Pattern 16: Natural month names (Jan, January, etc.)
    month_names = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6,
        'jul': 7, 'july': 7, 'aug': 8, 'august': 8, 'sep': 9, 'september': 9,
        'oct': 10, 'october': 10, 'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }
    
    # Look for "in January", "during March", etc.
    for month_name, month_num in month_names.items():
        if re.search(rf'\b(?:in|during)\s+{month_name}\b', q):
            # Assume current year unless specified
            year = now.year
            year_match = re.search(rf'\b(?:in|during)\s+{month_name}\s+(\d{{4}})\b', q)
            if year_match:
                year = int(year_match.group(1))
            
            start_of_month = datetime(year, month_num, 1)
            if month_num == 12:
                end_of_month = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end_of_month = datetime(year, month_num + 1, 1) - timedelta(seconds=1)
            
            return start_of_month.isoformat(), end_of_month.isoformat()
    
    # No time window found
    return None, None


def parse_time_window(question: str) -> Tuple[Optional[str], Optional[str]]:
    """Legacy function - now calls the advanced version."""
    return extract_time_window_advanced(question)


def domain_of(email: str) -> str:
    return email.split("@")[-1].lower()


def answer_question(question: str) -> str:
    q = question.strip()
    if not q:
        return "Please provide a question."

    # Try SQL agent first
    sql, sql_err = generate_sql(q)
    if sql_err:
        # If SQL gen unavailable, proceed to intent-based flow
        pass
    elif sql:
        cols, rows, run_err = run_sql_readonly(sql)
        if run_err:
            return format_error_natural(f"SQL execution error: {run_err}", q)
        
        # Render a concise tabular or aggregate response
        if not rows:
            raw_result = "No results."
        elif len(cols) == 1 and len(rows) == 1:
            raw_result = f"{cols[0]}: {rows[0][0]}"
        else:
            # Otherwise, render top 20 rows
            header = " | ".join(cols)
            body_lines = [" | ".join(str(v) for v in r) for r in rows[:20]]
            if len(rows) > 20:
                body_lines.append(f"... ({len(rows)-20} more)")
            raw_result = "\n".join([header] + body_lines)
        
        # Format with natural language if configured
        if formatter_is_configured():
            formatted = format_response_natural(q, raw_result)
            return formatted.formatted_text
        else:
            return raw_result

    # Try simple keyword-based intent detection first
    metric = None
    q_lower = q.lower()
    
    if any(word in q_lower for word in ['sent', 'send', 'total emails']):
        metric = 'sent'
    elif any(word in q_lower for word in ['opened', 'open', 'opens']):
        metric = 'opened'
    elif any(word in q_lower for word in ['replied', 'reply', 'replies', 'responded']):
        metric = 'replied'
    elif any(word in q_lower for word in ['bounced', 'bounce', 'bounces']):
        metric = 'bounced'
    
    # If no metric detected, try LLM parsing
    if metric is None:
        intent = parse_with_llm(q)
        if intent.error:
            # Fall back to guidance if not configured
            return intent.error
        metric = intent.metric
    
    if metric is None:
        return (
            "I can answer: sent, opened, replied (incl. speed), bounced by domain. "
            "Try questions like 'How many emails were opened last week?'."
        )

    # Advanced time window extraction using simple NLP
    start_date, end_date = parse_time_simple(q)
    start_iso = start_date.isoformat() if start_date else None
    end_iso = end_date.isoformat() if end_date else None

    conn = connect(readonly=True)
    try:
        cur = conn.cursor()
        where = []
        params = []
        if start_iso:
            where.append("sent_at >= ?")
            params.append(start_iso)
        if end_iso:
            where.append("sent_at <= ?")
            params.append(end_iso)
        where_sql = (" WHERE " + " AND ".join(where)) if where else ""

        if metric == "sent":
            cur.execute(f"SELECT COUNT(*) FROM email_events{where_sql}", params)
            (count,) = cur.fetchone()
            scope = " in the specified window" if where else ""
            time_context = " (last week)" if "last week" in q.lower() else ""
            raw_result = f"Total emails sent{scope}: {count:,}{time_context}"
            
            # Format with natural language if configured
            if formatter_is_configured():
                context = {"metric": "sent", "time_window": time_context.strip() if time_context else None}
                formatted = format_response_natural(q, raw_result, context)
                return formatted.formatted_text
            else:
                return raw_result

        if metric == "opened":
            cur.execute(f"SELECT COUNT(*) FROM email_events WHERE opened_at IS NOT NULL" + (" AND " + " AND ".join(where) if where else ""), params)
            (count,) = cur.fetchone()
            scope = " in the specified window" if where else ""
            time_context = " (last week)" if "last week" in q.lower() else ""
            raw_result = f"Total emails opened{scope}: {count:,}{time_context}"
            
            # Format with natural language if configured
            if formatter_is_configured():
                context = {"metric": "opened", "time_window": time_context.strip() if time_context else None}
                formatted = format_response_natural(q, raw_result, context)
                return formatted.formatted_text
            else:
                return raw_result

        if metric == "replied":
            cur.execute(
                "SELECT replied_at, sent_at FROM email_events WHERE replied_at IS NOT NULL"
                + (" AND " + " AND ".join(where) if where else ""),
                params,
            )
            rows = cur.fetchall()
            count = len(rows)
            if count == 0:
                scope = " in the specified window" if where else ""
                time_context = " (last week)" if "last week" in q.lower() else ""
                raw_result = f"Total people who replied{scope}: 0{time_context}"
            else:
                # Compute response times in hours
                diffs = []
                for replied_at, sent_at in rows:
                    try:
                        ra = datetime.fromisoformat(replied_at)
                        sa = datetime.fromisoformat(sent_at)
                        diffs.append((ra - sa).total_seconds() / 3600.0)
                    except Exception:
                        continue
                avg_hours = sum(diffs) / len(diffs) if diffs else 0.0
                scope = " in the specified window" if where else ""
                time_context = " (last week)" if "last week" in q.lower() else ""
                raw_result = f"Total people who replied{scope}: {count:,}{time_context}. Average reply time: {avg_hours:.1f} hours"
            
            # Format with natural language if configured
            if formatter_is_configured():
                context = {"metric": "replied", "time_window": time_context.strip() if time_context else None}
                formatted = format_response_natural(q, raw_result, context)
                return formatted.formatted_text
            else:
                return raw_result

        if metric == "bounced":
            cur.execute(
                "SELECT email_address, bounced FROM email_events"
                + where_sql,
                params,
            )
            by_domain: Dict[str, int] = defaultdict(int)
            total = 0
            for email_address, bounced in cur.fetchall():
                if bounced:
                    by_domain[domain_of(email_address)] += 1
                    total += 1
            if total == 0:
                scope = " in the specified window" if where else ""
                time_context = " (last week)" if "last week" in q.lower() else ""
                raw_result = f"Total bounced emails{scope}: 0{time_context}"
            else:
                # Format grouped output
                domain_parts = []
                for dom, cnt in sorted(by_domain.items(), key=lambda x: (-x[1], x[0])):
                    domain_parts.append(f"{dom}: {cnt:,}")
                
                scope = " in the specified window" if where else ""
                time_context = " (last week)" if "last week" in q.lower() else ""
                raw_result = f"Total bounced emails{scope}: {total:,}{time_context}. By domain: " + ", ".join(domain_parts)
            
            # Format with natural language if configured
            if formatter_is_configured():
                context = {"metric": "bounced", "time_window": time_context.strip() if time_context else None}
                formatted = format_response_natural(q, raw_result, context)
                return formatted.formatted_text
            else:
                return raw_result

        return (
            "Field not available. Try sent, opened, replied (with speed), or bounced by domain."
        )
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask questions about the email campaign")
    parser.add_argument("question", type=str, help="Natural-language question in quotes")
    args = parser.parse_args()
    print(answer_question(args.question))


if __name__ == "__main__":
    main()


