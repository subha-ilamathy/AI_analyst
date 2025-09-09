#!/usr/bin/env python3
"""Unit tests for AI Analyst Email Campaign components."""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sql_agent import generate_sql, run_sql_readonly, is_safe_select, is_configured as sql_configured
from src.llm import parse_with_llm, is_configured as llm_configured
from src.utils.time_parser import parse_time_simple
from src.utils.response_formatter import format_response_natural, format_error_natural, is_configured as formatter_configured


class TestSQLAgent(unittest.TestCase):
    """Test cases for SQL Agent functionality."""
    
    def test_is_safe_select_valid_queries(self):
        """Test that valid SELECT queries pass safety checks."""
        valid_queries = [
            "SELECT COUNT(*) FROM email_events",
            "SELECT * FROM email_events WHERE opened_at IS NOT NULL",
            "SELECT email_address, COUNT(*) FROM email_events GROUP BY email_address",
            "SELECT * FROM email_events e JOIN contacts c ON e.contact_id = c.id",
            "SELECT COUNT(*) as total FROM email_events WHERE sent_at >= '2024-01-01'",
        ]
        
        for query in valid_queries:
            with self.subTest(query=query):
                self.assertTrue(is_safe_select(query), f"Query should be safe: {query}")
    
    def test_is_safe_select_dangerous_queries(self):
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
    
    @patch('sql_agent.is_configured', return_value=False)
    def test_generate_sql_no_api_key(self, mock_configured):
        """Test SQL generation when OpenAI is not configured."""
        result = generate_sql("How many emails were sent?")
        self.assertIsNone(result.sql)
        self.assertIsNotNone(result.error)
        self.assertIn("OpenAI API key not configured", result.error)
    
    @patch('sql_agent.is_configured', return_value=True)
    @patch('sql_agent.openai.chat.completions.create')
    def test_generate_sql_with_api_key(self, mock_create, mock_configured):
        """Test SQL generation when OpenAI is configured."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "SELECT COUNT(*) FROM email_events"
        mock_create.return_value = mock_response
        
        result = generate_sql("How many emails were sent?")
        self.assertEqual(result.sql, "SELECT COUNT(*) FROM email_events")
        self.assertIsNone(result.error)
    
    def test_run_sql_readonly_safe_query(self):
        """Test running a safe SQL query."""
        # This test would need a real database connection
        # For now, we'll test the safety check
        safe_query = "SELECT COUNT(*) FROM email_events"
        self.assertTrue(is_safe_select(safe_query))


class TestLLM(unittest.TestCase):
    """Test cases for LLM functionality."""
    
    @patch('llm.is_configured', return_value=False)
    def test_parse_with_llm_no_api_key(self, mock_configured):
        """Test LLM parsing when OpenAI is not configured."""
        result = parse_with_llm("How many emails were sent?")
        self.assertIsNone(result.metric)
        self.assertIsNotNone(result.error)
        self.assertIn("OpenAI API key not configured", result.error)
    
    @patch('llm.is_configured', return_value=True)
    @patch('llm.openai.chat.completions.create')
    def test_parse_with_llm_with_api_key(self, mock_create, mock_configured):
        """Test LLM parsing when OpenAI is configured."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"metric": "sent", "confidence": 0.9}'
        mock_create.return_value = mock_response
        
        result = parse_with_llm("How many emails were sent?")
        self.assertEqual(result.metric, "sent")
        self.assertIsNone(result.error)
    
    def test_llm_configuration_check(self):
        """Test LLM configuration detection."""
        # Test with no API key
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(llm_configured())
        
        # Test with API key
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            self.assertTrue(llm_configured())


class TestTimeParser(unittest.TestCase):
    """Test cases for Time Parser functionality."""
    
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


class TestResponseFormatter(unittest.TestCase):
    """Test cases for Response Formatter functionality."""
    
    @patch('utils.response_formatter.is_configured', return_value=False)
    def test_format_response_natural_no_api_key(self, mock_configured):
        """Test response formatting when OpenAI is not configured."""
        result = format_response_natural(
            "How many emails were sent?",
            "Total emails sent: 50"
        )
        self.assertEqual(result.formatted_text, "Total emails sent: 50")
        self.assertIsNotNone(result.error)
        self.assertIn("OpenAI API key not configured", result.error)
    
    @patch('utils.response_formatter.is_configured', return_value=True)
    @patch('utils.response_formatter.openai.chat.completions.create')
    def test_format_response_natural_with_api_key(self, mock_create, mock_configured):
        """Test response formatting when OpenAI is configured."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Great question! You sent a total of 50 emails in your campaign."
        mock_create.return_value = mock_response
        
        result = format_response_natural(
            "How many emails were sent?",
            "Total emails sent: 50"
        )
        self.assertEqual(result.formatted_text, "Great question! You sent a total of 50 emails in your campaign.")
        self.assertIsNone(result.error)
    
    @patch('utils.response_formatter.is_configured', return_value=False)
    def test_format_error_natural_no_api_key(self, mock_configured):
        """Test error formatting when OpenAI is not configured."""
        result = format_error_natural("Database error", "How many emails were sent?")
        self.assertEqual(result, "I encountered an issue: Database error")
    
    @patch('utils.response_formatter.is_configured', return_value=True)
    @patch('utils.response_formatter.openai.chat.completions.create')
    def test_format_error_natural_with_api_key(self, mock_create, mock_configured):
        """Test error formatting when OpenAI is configured."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "I'm sorry, but I encountered a database error while processing your question about email counts."
        mock_create.return_value = mock_response
        
        result = format_error_natural("Database error", "How many emails were sent?")
        self.assertEqual(result, "I'm sorry, but I encountered a database error while processing your question about email counts.")
    
    def test_formatter_configuration_check(self):
        """Test formatter configuration detection."""
        # Test with no API key
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(formatter_configured())
        
        # Test with API key
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            self.assertTrue(formatter_configured())


class TestIntegration(unittest.TestCase):
    """Integration tests for component interactions."""
    
    def test_time_parser_with_context(self):
        """Test time parser with context information."""
        query = "How many emails were opened last week?"
        start_date, end_date = parse_time_simple(query)
        
        # Should extract time window
        self.assertIsNotNone(start_date)
        self.assertIsNotNone(end_date)
        
        # Should be approximately 7 days
        duration = end_date - start_date
        self.assertAlmostEqual(duration.days, 7, delta=1)
    
    @patch('utils.response_formatter.is_configured', return_value=True)
    @patch('utils.response_formatter.openai.chat.completions.create')
    def test_response_formatter_with_context(self, mock_create, mock_configured):
        """Test response formatter with context information."""
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Looking at last week's data, you sent 50 emails."
        mock_create.return_value = mock_response
        
        context = {
            "metric": "sent",
            "time_window": "last week"
        }
        
        result = format_response_natural(
            "How many emails were sent last week?",
            "Total emails sent: 50",
            context
        )
        
        self.assertEqual(result.formatted_text, "Looking at last week's data, you sent 50 emails.")
        self.assertIsNone(result.error)


def run_tests():
    """Run all unit tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestSQLAgent,
        TestLLM,
        TestTimeParser,
        TestResponseFormatter,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🧪 Running AI Analyst Email Campaign Unit Tests")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
