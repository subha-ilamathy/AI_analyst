#!/usr/bin/env python3
"""Simple unit tests for AI Analyst Email Campaign components."""

import unittest
import os
import sys
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sql_agent import is_safe_select
from src.utils.time_parser import parse_time_simple


class TestSQLSafety(unittest.TestCase):
    """Test SQL safety validation."""
    
    def test_safe_select_queries(self):
        """Test that valid SELECT queries pass safety checks."""
        safe_queries = [
            "SELECT COUNT(*) FROM email_events",
            "SELECT * FROM email_events WHERE opened_at IS NOT NULL",
            "SELECT email_address, COUNT(*) FROM email_events GROUP BY email_address",
            "SELECT * FROM email_events e JOIN contacts c ON e.contact_id = c.id",
            "SELECT COUNT(*) as total FROM email_events WHERE sent_at >= '2024-01-01'",
        ]
        
        for query in safe_queries:
            with self.subTest(query=query):
                self.assertTrue(is_safe_select(query), f"Query should be safe: {query}")
    
    def test_dangerous_queries_blocked(self):
        """Test that dangerous queries are blocked."""
        dangerous_queries = [
            "DROP TABLE email_events",
            "DELETE FROM email_events",
            "INSERT INTO email_events VALUES (1, 'test@example.com')",
            "UPDATE email_events SET opened_at = NOW()",
            "SELECT * FROM sqlite_master",
            "SELECT load_extension('evil.dll')",
            "SELECT * FROM email_events; DROP TABLE email_events;",
        ]
        
        for query in dangerous_queries:
            with self.subTest(query=query):
                self.assertFalse(is_safe_select(query), f"Query should be blocked: {query}")


class TestTimeParser(unittest.TestCase):
    """Test time parsing functionality."""
    
    def test_parse_last_week(self):
        """Test parsing 'last week' expressions."""
        start_date, end_date = parse_time_simple("How many emails were sent last week?")
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
        self.assertLess(start_date, end_date)
        
        # Check that it's approximately 7 days
        duration = end_date - start_date
        self.assertAlmostEqual(duration.days, 7, delta=1)
    
    def test_parse_yesterday(self):
        """Test parsing 'yesterday' expressions."""
        start_date, end_date = parse_time_simple("Show me opens from yesterday")
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
        
        # Check that it's approximately 1 day
        duration = end_date - start_date
        self.assertAlmostEqual(duration.days, 1, delta=1)
    
    def test_parse_this_month(self):
        """Test parsing 'this month' expressions."""
        start_date, end_date = parse_time_simple("What happened this month?")
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
        
        # Check that start_date is at the beginning of the month
        self.assertEqual(start_date.day, 1)
        self.assertEqual(start_date.hour, 0)
        self.assertEqual(start_date.minute, 0)
    
    def test_parse_specific_date(self):
        """Test parsing specific date expressions."""
        start_date, end_date = parse_time_simple("Show me data from January 2024")
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
        
        # Check that it's in January 2024
        self.assertEqual(start_date.year, 2024)
        self.assertEqual(start_date.month, 1)
    
    def test_parse_no_time_expression(self):
        """Test parsing queries with no time expressions."""
        start_date, end_date = parse_time_simple("What is the total bounce rate?")
        self.assertIsNone(start_date)
        self.assertIsNone(end_date)
    
    def test_parse_relative_days(self):
        """Test parsing relative day expressions."""
        start_date, end_date = parse_time_simple("How many bounced in the last 7 days?")
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
        
        # Check that it's approximately 7 days
        duration = end_date - start_date
        self.assertAlmostEqual(duration.days, 7, delta=1)


class TestCLIIntegration(unittest.TestCase):
    """Test CLI integration."""
    
    def test_time_parser_integration(self):
        """Test time parser integration with different query types."""
        test_cases = [
            ("How many emails were sent last week?", True),
            ("Show me opens from yesterday", True),
            ("What happened this month?", True),
            ("Show me data from January 2024", True),
            ("What is the total bounce rate?", False),
            ("How many people replied?", False),
        ]
        
        for query, should_have_time in test_cases:
            with self.subTest(query=query):
                start_date, end_date = parse_time_simple(query)
                if should_have_time:
                    self.assertIsNotNone(start_date, f"Query should have time: {query}")
                    self.assertIsNotNone(end_date, f"Query should have time: {query}")
                else:
                    self.assertIsNone(start_date, f"Query should not have time: {query}")
                    self.assertIsNone(end_date, f"Query should not have time: {query}")


def run_tests():
    """Run all unit tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestSQLSafety,
        TestTimeParser,
        TestCLIIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 Running Simple AI Analyst Email Campaign Unit Tests")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
