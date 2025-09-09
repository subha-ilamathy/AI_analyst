#!/usr/bin/env python3
"""CLI entry point for AI Analyst Email Campaign."""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import with absolute imports
from src.cli import answer_question
from src.data.db import init_schema
from src.data.seed import seed_database


def main():
    """Main CLI application."""
    parser = argparse.ArgumentParser(
        description="Ask questions about your email campaign",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        python cli_main.py "How many emails were sent last week?"
        python cli_main.py "What's the bounce rate by domain?"
        python cli_main.py "How many people replied, and how quickly?"
        python cli_main.py --init-db
        """
    )
    
    parser.add_argument(
        "question", 
        nargs="?", 
        type=str, 
        help="Natural-language question about your email campaign"
    )
    
    parser.add_argument(
        "--init-db", 
        action="store_true", 
        help="Initialize database with sample data"
    )
    
    parser.add_argument(
        "--seed-count", 
        type=int, 
        default=100, 
        help="Number of sample records to create (default: 100)"
    )
    
    args = parser.parse_args()
    
    # Initialize database if requested
    if args.init_db:
        print("🔧 Initializing database...")
        try:
            conn, _ = init_schema()
            conn.close()
            seed_database(args.seed_count)
            print(f"✅ Database initialized with {args.seed_count} sample records!")
            return
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            sys.exit(1)
    
    # Check if question is provided
    if not args.question:
        print("❌ Please provide a question or use --init-db to initialize the database")
        print("\nExample:")
        print('  python cli_main.py "How many emails were sent last week?"')
        sys.exit(1)
    
    # Ensure database exists
    try:
        conn, _ = init_schema()
        conn.close()
        
        # Check if we have data
        from src.data.db import connect
        conn = connect(readonly=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM email_events")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            print("📊 No data found. Seeding database with sample data...")
            seed_database(args.seed_count)
            print(f"✅ Database seeded with {args.seed_count} records!")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    
    # Answer the question
    try:
        print(f"🤖 Question: {args.question}")
        print("=" * 50)
        
        result = answer_question(args.question)
        print(f"📊 Answer: {result}")
        
    except Exception as e:
        print(f"❌ Error processing question: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
