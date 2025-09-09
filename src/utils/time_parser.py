"""Simplified NLP parsing that works without heavy dependencies."""

import re
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from dateutil import parser as dtparser


@dataclass
class TimeExpression:
    """Represents a parsed time expression."""
    text: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    confidence: float
    expression_type: str
    entities: List[str]


class SimpleTimeParser:
    """Simplified time parsing using pattern matching and dateutil."""
    
    def __init__(self):
        # Time expression patterns with confidence scores
        self.patterns = [
            # Last week patterns
            (r'\blast\s+week\b', self._parse_last_week, 0.9),
            (r'\bprevious\s+week\b', self._parse_last_week, 0.9),
            (r'\bpast\s+week\b', self._parse_last_week, 0.8),
            
            # This week patterns
            (r'\bthis\s+week\b', self._parse_this_week, 0.9),
            (r'\bcurrent\s+week\b', self._parse_this_week, 0.8),
            
            # Last month patterns
            (r'\blast\s+month\b', self._parse_last_month, 0.9),
            (r'\bprevious\s+month\b', self._parse_last_month, 0.9),
            (r'\bpast\s+month\b', self._parse_last_month, 0.8),
            
            # This month patterns
            (r'\bthis\s+month\b', self._parse_this_month, 0.9),
            (r'\bcurrent\s+month\b', self._parse_this_month, 0.8),
            
            # Last year patterns
            (r'\blast\s+year\b', self._parse_last_year, 0.9),
            (r'\bprevious\s+year\b', self._parse_last_year, 0.9),
            (r'\bpast\s+year\b', self._parse_last_year, 0.8),
            
            # This year patterns
            (r'\bthis\s+year\b', self._parse_this_year, 0.9),
            (r'\bcurrent\s+year\b', self._parse_this_year, 0.8),
            
            # Yesterday patterns
            (r'\byesterday\b', self._parse_yesterday, 0.95),
            (r'\bday\s+before\b', self._parse_yesterday, 0.8),
            (r'\bprevious\s+day\b', self._parse_yesterday, 0.8),
            
            # Today patterns
            (r'\btoday\b', self._parse_today, 0.95),
            (r'\bcurrent\s+day\b', self._parse_today, 0.8),
            (r'\bpresent\s+day\b', self._parse_today, 0.7),
            
            # Relative days patterns
            (r'\blast\s+(\d+)\s+days?\b', self._parse_last_n_days, 0.8),
            (r'\bpast\s+(\d+)\s+days?\b', self._parse_last_n_days, 0.8),
            (r'\b(\d+)\s+days?\s+ago\b', self._parse_n_days_ago, 0.8),
            
            # Relative weeks patterns
            (r'\blast\s+(\d+)\s+weeks?\b', self._parse_last_n_weeks, 0.8),
            (r'\bpast\s+(\d+)\s+weeks?\b', self._parse_last_n_weeks, 0.8),
            (r'\b(\d+)\s+weeks?\s+ago\b', self._parse_n_weeks_ago, 0.8),
            
            # Relative months patterns
            (r'\blast\s+(\d+)\s+months?\b', self._parse_last_n_months, 0.8),
            (r'\bpast\s+(\d+)\s+months?\b', self._parse_last_n_months, 0.8),
            (r'\b(\d+)\s+months?\s+ago\b', self._parse_n_months_ago, 0.8),
            
            # Since patterns
            (r'\bsince\s+([^,]+?)(?:\s|$)', self._parse_since, 0.8),
            
            # Between patterns
            (r'\bbetween\s+([^,]+?)\s+and\s+([^,]+?)(?:\s|$)', self._parse_between, 0.8),
            (r'\bfrom\s+([^,]+?)\s+to\s+([^,]+?)(?:\s|$)', self._parse_from_to, 0.8),
            (r'\bfrom\s+([^,]+?)\s+until\s+([^,]+?)(?:\s|$)', self._parse_from_until, 0.8),
            
            # On specific date patterns
            (r'\bon\s+([^,]+?)(?:\s|$)', self._parse_on_date, 0.7),
        ]
    
    def parse_time_expression(self, text: str) -> List[TimeExpression]:
        """Parse time expressions from text."""
        expressions = []
        text_lower = text.lower()
        
        for pattern, parser_func, confidence in self.patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    expr = parser_func(match, text)
                    if expr:
                        expr.confidence = confidence
                        expressions.append(expr)
                except Exception:
                    continue
        
        # Try dateutil parsing for unmatched text
        if not expressions:
            expr = self._parse_with_dateutil(text)
            if expr:
                expressions.append(expr)
        
        # Sort by confidence and remove duplicates
        unique_expressions = self._deduplicate_expressions(expressions)
        return sorted(unique_expressions, key=lambda x: x.confidence, reverse=True)
    
    def _parse_last_week(self, match, text: str) -> TimeExpression:
        """Parse 'last week' expressions."""
        now = datetime.now()
        today_weekday = now.weekday()  # Monday=0
        start_of_this_week = now - timedelta(days=today_weekday)
        start_of_last_week = start_of_this_week - timedelta(days=7)
        end_of_last_week = start_of_last_week + timedelta(days=6)
        
        return TimeExpression(
            text=text,
            start_date=start_of_last_week.replace(hour=0, minute=0, second=0),
            end_date=end_of_last_week.replace(hour=23, minute=59, second=59),
            confidence=0.9,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_this_week(self, match, text: str) -> TimeExpression:
        """Parse 'this week' expressions."""
        now = datetime.now()
        today_weekday = now.weekday()
        start_of_this_week = now - timedelta(days=today_weekday)
        
        return TimeExpression(
            text=text,
            start_date=start_of_this_week.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.9,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_last_month(self, match, text: str) -> TimeExpression:
        """Parse 'last month' expressions."""
        now = datetime.now()
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0)
        last_month = first_of_this_month - timedelta(days=1)
        first_of_last_month = last_month.replace(day=1)
        last_day_of_last_month = last_month
        
        return TimeExpression(
            text=text,
            start_date=first_of_last_month,
            end_date=last_day_of_last_month.replace(hour=23, minute=59, second=59),
            confidence=0.9,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_this_month(self, match, text: str) -> TimeExpression:
        """Parse 'this month' expressions."""
        now = datetime.now()
        first_of_this_month = now.replace(day=1, hour=0, minute=0, second=0)
        
        return TimeExpression(
            text=text,
            start_date=first_of_this_month,
            end_date=now,
            confidence=0.9,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_last_year(self, match, text: str) -> TimeExpression:
        """Parse 'last year' expressions."""
        now = datetime.now()
        start_of_this_year = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        start_of_last_year = start_of_this_year.replace(year=now.year - 1)
        end_of_last_year = start_of_this_year - timedelta(seconds=1)
        
        return TimeExpression(
            text=text,
            start_date=start_of_last_year,
            end_date=end_of_last_year,
            confidence=0.9,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_this_year(self, match, text: str) -> TimeExpression:
        """Parse 'this year' expressions."""
        now = datetime.now()
        start_of_this_year = now.replace(month=1, day=1, hour=0, minute=0, second=0)
        
        return TimeExpression(
            text=text,
            start_date=start_of_this_year,
            end_date=now,
            confidence=0.9,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_yesterday(self, match, text: str) -> TimeExpression:
        """Parse 'yesterday' expressions."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        return TimeExpression(
            text=text,
            start_date=yesterday.replace(hour=0, minute=0, second=0),
            end_date=yesterday.replace(hour=23, minute=59, second=59),
            confidence=0.95,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_today(self, match, text: str) -> TimeExpression:
        """Parse 'today' expressions."""
        now = datetime.now()
        
        return TimeExpression(
            text=text,
            start_date=now.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.95,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_last_n_days(self, match, text: str) -> TimeExpression:
        """Parse 'last N days' expressions."""
        num_days = int(match.group(1))
        now = datetime.now()
        start = now - timedelta(days=num_days)
        
        return TimeExpression(
            text=text,
            start_date=start.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.8,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_n_days_ago(self, match, text: str) -> TimeExpression:
        """Parse 'N days ago' expressions."""
        num_days = int(match.group(1))
        now = datetime.now()
        start = now - timedelta(days=num_days)
        
        return TimeExpression(
            text=text,
            start_date=start.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.8,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_last_n_weeks(self, match, text: str) -> TimeExpression:
        """Parse 'last N weeks' expressions."""
        num_weeks = int(match.group(1))
        now = datetime.now()
        start = now - timedelta(weeks=num_weeks)
        
        return TimeExpression(
            text=text,
            start_date=start.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.8,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_n_weeks_ago(self, match, text: str) -> TimeExpression:
        """Parse 'N weeks ago' expressions."""
        num_weeks = int(match.group(1))
        now = datetime.now()
        start = now - timedelta(weeks=num_weeks)
        
        return TimeExpression(
            text=text,
            start_date=start.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.8,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_last_n_months(self, match, text: str) -> TimeExpression:
        """Parse 'last N months' expressions."""
        num_months = int(match.group(1))
        now = datetime.now()
        start = now - timedelta(days=num_months * 30)  # Approximate
        
        return TimeExpression(
            text=text,
            start_date=start.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.8,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_n_months_ago(self, match, text: str) -> TimeExpression:
        """Parse 'N months ago' expressions."""
        num_months = int(match.group(1))
        now = datetime.now()
        start = now - timedelta(days=num_months * 30)  # Approximate
        
        return TimeExpression(
            text=text,
            start_date=start.replace(hour=0, minute=0, second=0),
            end_date=now,
            confidence=0.8,
            expression_type='relative',
            entities=[match.group(0)]
        )
    
    def _parse_since(self, match, text: str) -> TimeExpression:
        """Parse 'since X' expressions."""
        date_str = match.group(1).strip()
        try:
            start_date = dtparser.parse(date_str, fuzzy=True)
            now = datetime.now()
            
            return TimeExpression(
                text=text,
                start_date=start_date,
                end_date=now,
                confidence=0.8,
                expression_type='range',
                entities=[date_str]
            )
        except:
            return None
    
    def _parse_between(self, match, text: str) -> TimeExpression:
        """Parse 'between X and Y' expressions."""
        start_str = match.group(1).strip()
        end_str = match.group(2).strip()
        try:
            start_date = dtparser.parse(start_str, fuzzy=True)
            end_date = dtparser.parse(end_str, fuzzy=True)
            
            if end_date < start_date:
                return None
            
            return TimeExpression(
                text=text,
                start_date=start_date,
                end_date=end_date.replace(hour=23, minute=59, second=59),
                confidence=0.8,
                expression_type='range',
                entities=[start_str, end_str]
            )
        except:
            return None
    
    def _parse_from_to(self, match, text: str) -> TimeExpression:
        """Parse 'from X to Y' expressions."""
        return self._parse_between(match, text)
    
    def _parse_from_until(self, match, text: str) -> TimeExpression:
        """Parse 'from X until Y' expressions."""
        return self._parse_between(match, text)
    
    def _parse_on_date(self, match, text: str) -> TimeExpression:
        """Parse 'on X' expressions."""
        date_str = match.group(1).strip()
        try:
            date = dtparser.parse(date_str, fuzzy=True)
            
            return TimeExpression(
                text=text,
                start_date=date.replace(hour=0, minute=0, second=0),
                end_date=date.replace(hour=23, minute=59, second=59),
                confidence=0.7,
                expression_type='absolute',
                entities=[date_str]
            )
        except:
            return None
    
    def _parse_with_dateutil(self, text: str) -> Optional[TimeExpression]:
        """Parse using dateutil fuzzy parsing."""
        try:
            parsed_date = dtparser.parse(text, fuzzy=True)
            now = datetime.now()
            
            # Only add if it's a reasonable date
            if abs((parsed_date - now).days) < 365 * 10:  # Within 10 years
                return TimeExpression(
                    text=text,
                    start_date=parsed_date,
                    end_date=parsed_date,
                    confidence=0.6,
                    expression_type='absolute',
                    entities=[text]
                )
        except:
            pass
        
        return None
    
    def _deduplicate_expressions(self, expressions: List[TimeExpression]) -> List[TimeExpression]:
        """Remove duplicate expressions."""
        if not expressions:
            return []
        
        unique_expressions = []
        for expr in expressions:
            is_duplicate = False
            for unique_expr in unique_expressions:
                if (abs((expr.start_date or datetime.min) - (unique_expr.start_date or datetime.min)) < timedelta(minutes=1) and
                    abs((expr.end_date or datetime.min) - (unique_expr.end_date or datetime.min)) < timedelta(minutes=1)):
                    is_duplicate = True
                    if expr.confidence > unique_expr.confidence:
                        unique_expressions.remove(unique_expr)
                        unique_expressions.append(expr)
                    break
            
            if not is_duplicate:
                unique_expressions.append(expr)
        
        return unique_expressions
    
    def get_best_time_window(self, text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the best time window from parsed expressions."""
        expressions = self.parse_time_expression(text)
        
        if not expressions:
            return None, None
        
        best_expr = expressions[0]
        return best_expr.start_date, best_expr.end_date


# Global instance
simple_time_parser = SimpleTimeParser()


def parse_time_simple(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse time expressions using simple pattern matching."""
    return simple_time_parser.get_best_time_window(text)


__all__ = ["SimpleTimeParser", "TimeExpression", "parse_time_simple"]
