#!/usr/bin/env python3
"""Test script for advanced NLP capabilities."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.advanced_nlp import parse_time_advanced, classify_query_intent, AdvancedTimeParser


def test_time_parsing():
    """Test advanced time parsing capabilities."""
    print("=== Testing Advanced Time Parsing ===")
    
    test_queries = [
        "How many emails were sent last week?",
        "Show me opens from yesterday",
        "What happened this month?",
        "Emails sent in the past 7 days",
        "Data from January 2024",
        "Between 2024-01-01 and 2024-01-31",
        "Since 2024-06-01",
        "On 2024-12-25",
        "From 2024-01-01 to 2024-01-31",
        "Last 3 months",
        "This year",
        "Last year",
        "Show me data from the previous quarter",
        "What happened during the past fortnight",
        "Emails from the beginning of this year"
    ]
    
    for query in test_queries:
        start_date, end_date = parse_time_advanced(query)
        print(f"Query: {query}")
        print(f"  Start: {start_date}")
        print(f"  End: {end_date}")
        print()


def test_intent_classification():
    """Test semantic intent classification."""
    print("=== Testing Intent Classification ===")
    
    test_queries = [
        "How many emails were sent?",
        "What's the total number of opened emails?",
        "Count the replies we received",
        "Show me the bounce rate",
        "How many people responded to our campaign?",
        "What's the open rate for our emails?",
        "Give me the number of delivered emails",
        "How many emails failed to deliver?",
        "Show me replies grouped by domain",
        "What's the breakdown by email domain?"
    ]
    
    for query in test_queries:
        intent, confidence = classify_query_intent(query)
        print(f"Query: {query}")
        print(f"  Intent: {intent}")
        print(f"  Confidence: {confidence:.3f}")
        print()


def test_detailed_time_parsing():
    """Test detailed time parsing with expressions."""
    print("=== Testing Detailed Time Parsing ===")
    
    parser = AdvancedTimeParser()
    
    test_queries = [
        "Show me data from last week",
        "What happened yesterday",
        "Emails sent this month",
        "Data from the past 30 days",
        "Results from January 2024",
        "Between Christmas and New Year",
        "Since the beginning of the year"
    ]
    
    for query in test_queries:
        print(f"Query: {query}")
        expressions = parser.parse_time_expression(query)
        
        for i, expr in enumerate(expressions):
            print(f"  Expression {i+1}:")
            print(f"    Text: {expr.text}")
            print(f"    Type: {expr.expression_type}")
            print(f"    Start: {expr.start_date}")
            print(f"    End: {expr.end_date}")
            print(f"    Confidence: {expr.confidence:.3f}")
            print(f"    Entities: {expr.entities}")
        print()


if __name__ == "__main__":
    print("Advanced NLP Testing for AI Analyst Email Campaign")
    print("=" * 60)
    
    try:
        test_time_parsing()
        test_intent_classification()
        test_detailed_time_parsing()
    except Exception as e:
        print(f"Error during testing: {e}")
        print("Note: Some features require additional dependencies.")
        print("Install with: pip install spacy sentence-transformers scikit-learn")
        print("Then download spaCy model: python -m spacy download en_core_web_sm")
