#!/usr/bin/env python3
"""Streamlit web app for AI Analyst Email Campaign."""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

from src.cli import answer_question
from src.db import connect, init_schema
from src.seed import seed_database
from src.simple_nlp import parse_time_simple
from src.response_formatter import is_configured as formatter_is_configured


def init_database():
    """Initialize database if needed."""
    try:
        conn, _ = init_schema()
        conn.close()
        
        # Check if we have data
        conn = connect(readonly=True)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM email_events")
        count = cursor.fetchone()[0]
        conn.close()
        
        if count == 0:
            st.info("No data found. Seeding database with sample data...")
            seed_database(140)
            st.success("Database seeded successfully!")
        
        return True
    except Exception as e:
        st.error(f"Database initialization failed: {e}")
        return False


def get_campaign_stats():
    """Get basic campaign statistics."""
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        
        # Total stats
        cursor.execute("SELECT COUNT(*) FROM email_events")
        total_sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM email_events WHERE opened_at IS NOT NULL")
        total_opened = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM email_events WHERE replied_at IS NOT NULL")
        total_replied = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM email_events WHERE bounced = 1")
        total_bounced = cursor.fetchone()[0]
        
        # Open rate
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        
        # Reply rate
        reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
        
        # Bounce rate
        bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
        
        return {
            'total_sent': total_sent,
            'total_opened': total_opened,
            'total_replied': total_replied,
            'total_bounced': total_bounced,
            'open_rate': open_rate,
            'reply_rate': reply_rate,
            'bounce_rate': bounce_rate
        }
    finally:
        conn.close()


def get_domain_breakdown():
    """Get email breakdown by domain."""
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN email_address LIKE '%@gmail.com' THEN 'gmail.com'
                    WHEN email_address LIKE '%@outlook.com' THEN 'outlook.com'
                    WHEN email_address LIKE '%@yahoo.com' THEN 'yahoo.com'
                    WHEN email_address LIKE '%@proton.me' THEN 'proton.me'
                    ELSE 'company.com'
                END as domain,
                COUNT(*) as total,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
                SUM(CASE WHEN bounced = 1 THEN 1 ELSE 0 END) as bounced
            FROM email_events 
            GROUP BY domain
            ORDER BY total DESC
        """)
        
        results = cursor.fetchall()
        return pd.DataFrame(results, columns=['domain', 'total', 'opened', 'replied', 'bounced'])
    finally:
        conn.close()


def get_time_series_data():
    """Get time series data for charts."""
    conn = connect(readonly=True)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                DATE(sent_at) as date,
                COUNT(*) as sent,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                SUM(CASE WHEN replied_at IS NOT NULL THEN 1 ELSE 0 END) as replied,
                SUM(CASE WHEN bounced = 1 THEN 1 ELSE 0 END) as bounced
            FROM email_events 
            GROUP BY DATE(sent_at)
            ORDER BY date
        """)
        
        results = cursor.fetchall()
        return pd.DataFrame(results, columns=['date', 'sent', 'opened', 'replied', 'bounced'])
    finally:
        conn.close()


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="AI Analyst Email Campaign",
        page_icon="📧",
        layout="wide"
    )
    
    st.title("📧 AI Analyst Email Campaign")
    st.markdown("Analyze your email campaign performance with natural language queries")
  
    # Initialize database
    if not init_database():
        st.stop()
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Dashboard", "Chat Interface", "Data Explorer"]
    )
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Chat Interface":
        show_query_interface()
    elif page == "Data Explorer":
        show_data_explorer()


def show_dashboard():
    """Show the main dashboard."""
    st.header("📊 Campaign Dashboard")
    
    # Get statistics
    stats = get_campaign_stats()
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Sent",
            value=f"{stats['total_sent']:,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Open Rate",
            value=f"{stats['open_rate']:.1f}%",
            delta=f"{stats['total_opened']:,} opened"
        )
    
    with col3:
        st.metric(
            label="Reply Rate",
            value=f"{stats['reply_rate']:.1f}%",
            delta=f"{stats['total_replied']:,} replied"
        )
    
    with col4:
        st.metric(
            label="Bounce Rate",
            value=f"{stats['bounce_rate']:.1f}%",
            delta=f"{stats['total_bounced']:,} bounced"
        )
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Performance Over Time")
        time_data = get_time_series_data()
        
        if not time_data.empty:
            fig = px.line(
                time_data, 
                x='date', 
                y=['sent', 'opened', 'replied', 'bounced'],
                title="Email Performance Over Time",
                labels={'value': 'Count', 'date': 'Date'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time series data available")
    
    with col2:
        st.subheader("🌐 Domain Breakdown")
        domain_data = get_domain_breakdown()
        
        if not domain_data.empty:
            fig = px.pie(
                domain_data, 
                values='total', 
                names='domain',
                title="Emails by Domain"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No domain data available")
    
    # Domain performance table
    st.subheader("📋 Domain Performance")
    if not domain_data.empty:
        # Calculate rates
        domain_data['open_rate'] = (domain_data['opened'] / domain_data['total'] * 100).round(1)
        domain_data['reply_rate'] = (domain_data['replied'] / domain_data['total'] * 100).round(1)
        domain_data['bounce_rate'] = (domain_data['bounced'] / domain_data['total'] * 100).round(1)
        
        st.dataframe(
            domain_data[['domain', 'total', 'opened', 'replied', 'bounced', 'open_rate', 'reply_rate', 'bounce_rate']],
            use_container_width=True
        )


def show_query_interface():
    """Show the chat-like query interface."""
    st.header("💬 Chat with Your Email Campaign Analyst")
    
    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize processing flag
    if "processing_example" not in st.session_state:
        st.session_state.processing_example = False
    
    # Welcome message
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Hi! I'm your email campaign analyst. Ask me anything about your campaign performance - like 'How many emails were sent?' or 'What's our bounce rate?'"
        })
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Process example query if flag is set
    if st.session_state.processing_example:
        query = st.session_state.example_query
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(query)
        
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": query})
        
        # Display analyzing message immediately
        with st.chat_message("assistant"):
            analyzing_msg = st.empty()
            analyzing_msg.markdown("🔄 Analyzing your question...")
        
        # Add analyzing message to chat history
        st.session_state.messages.append({"role": "assistant", "content": "🔄 Analyzing your question..."})
        
        # Generate and add assistant response
        try:
            result = answer_question(query)
            
            # Show time parsing if applicable
            start_date, end_date = parse_time_simple(query)
            if start_date and end_date:
                time_info = f"\n\n📅 *Time window detected: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}*"
                result += time_info
            
            # Replace the analyzing message with the actual result
            analyzing_msg.markdown(result)
            st.session_state.messages[-1] = {"role": "assistant", "content": result}
            
        except Exception as e:
            error_msg = f"Sorry, I encountered an error: {e}"
            analyzing_msg.error(error_msg)
            st.session_state.messages[-1] = {"role": "assistant", "content": error_msg}
        
        # Clear processing flag
        st.session_state.processing_example = False
        st.rerun()
    
    # Chat input
    if prompt := st.chat_input("Ask me about your email campaign..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response
        with st.chat_message("assistant"):
            # Show analyzing message in chat
            analyzing_msg = st.empty()
            analyzing_msg.markdown("🔄 Analyzing your question...")
            
            try:
                result = answer_question(prompt)
                
                # Show time parsing if applicable
                start_date, end_date = parse_time_simple(prompt)
                if start_date and end_date:
                    time_info = f"\n\n📅 *Time window detected: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}*"
                    result += time_info
                
                # Replace analyzing message with actual result
                analyzing_msg.markdown(result)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": result})
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {e}"
                analyzing_msg.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
    
    # Sidebar with example queries and stats
    with st.sidebar:
        st.subheader("💡 Try asking:")
        example_queries = [
            "How many emails were sent last week?",
            "Show me opens from yesterday",
            "What's the bounce rate by domain?",
            "How many people replied, and how quickly?",
            "What happened this month?",
            "Show me data from January 2024"
        ]
        
        for query in example_queries:
            if st.button(f"💬 {query}", key=f"example_{hash(query)}"):
                # Set processing flag
                st.session_state.processing_example = True
                st.session_state.example_query = query
                st.rerun()
        
        st.divider()
        
        # Clear chat button
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.processing_example = False
            st.rerun()
    

def show_data_explorer():
    """Show raw data explorer."""
    st.header("🔍 Data Explorer")
    
    # Data filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        show_bounced = st.checkbox("Show bounced emails only", value=False)
    
    with col2:
        show_opened = st.checkbox("Show opened emails only", value=False)
    
    with col3:
        show_replied = st.checkbox("Show replied emails only", value=False)
    
    # Build query
    where_conditions = []
    if show_bounced:
        where_conditions.append("bounced = 1")
    if show_opened:
        where_conditions.append("opened_at IS NOT NULL")
    if show_replied:
        where_conditions.append("replied_at IS NOT NULL")
    
    where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
    
    # Fetch data
    conn = connect(readonly=True)
    try:
        query = f"""
            SELECT 
                email_address,
                first_name,
                last_name,
                company,
                campaign_name,
                sent_at,
                delivered_at,
                opened_at,
                replied_at,
                bounced,
                CASE 
                    WHEN bounced = 1 THEN 'Bounced'
                    WHEN replied_at IS NOT NULL THEN 'Replied'
                    WHEN opened_at IS NOT NULL THEN 'Opened'
                    WHEN delivered_at IS NOT NULL THEN 'Delivered'
                    ELSE 'Sent'
                END as status
            FROM email_events 
            WHERE {where_clause}
            ORDER BY sent_at DESC
            LIMIT 1000
        """
        
        df = pd.read_sql_query(query, conn)
        
        if not df.empty:
            st.subheader(f"📋 Email Events ({len(df)} records)")
            
            # Status distribution
            status_counts = df['status'].value_counts()
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Records", len(df))
            
            with col2:
                st.metric("Unique Campaigns", df['campaign_name'].nunique())
            
            # Data table
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"email_campaign_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No data found with the selected filters")
    
    finally:
        conn.close()


if __name__ == "__main__":
    main()
