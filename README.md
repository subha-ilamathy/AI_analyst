# AI Analyst Email Campaign

Minimal CLI prototype that analyzes a mock email campaign database and answers natural-language questions like:

- How many emails were sent?
- How many were opened?
- How many people replied, and how quickly?
- How many emails bounced, grouped by domain?

## Setup

Requirements: Python 3.8+

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Seed the database with realistic mock data (~140 rows):

```bash
python -m src.seed
```

## Quick Start


1. **Launch the web app** (recommended):
   ```bash
   python run_app.py
   ```

2. **Use the CLI** for quick queries:
   ```bash
   python app.py "How many emails were sent last week?"
   ```

## Usage

### Web Interface (Recommended)

Launch the Streamlit web app:

```bash
python run_app.py
```

Or directly with Streamlit:

```bash
streamlit run streamlit_app.py
```

The web interface provides:
- 📊 **Dashboard**: Visual analytics with charts and metrics
- 💬 **Chat Interface**: Conversational natural language query processing with chat history
- 🔍 **Data Explorer**: Raw data exploration and filtering

### Chat Interface Features

The chat interface provides a conversational experience:

- **💬 Chat History**: Maintains conversation context across multiple questions
- **🎯 Quick Actions**: Click example queries to instantly ask them (shows user message from left, analyzing buffer, then response)
- **📊 Live Stats**: Real-time campaign metrics in the sidebar
- **🗑️ Clear Chat**: Reset conversation history anytime
- **⏱️ Time Detection**: Automatically detects and shows time windows
- **🤖 Natural Responses**: AI-powered conversational responses (when OpenAI is configured)
- **🔄 In-Chat Processing**: Analyzing messages appear in the chat window for better UX

### Command Line Interface

Quick entrypoint:

```bash
python app.py "How many emails were sent?"
```

Or using the module CLI:

```bash
python -m src.cli "How many emails bounced, grouped by domain?"
```

### Using OpenAI Features

The system uses OpenAI for two main features:

1. **Intent Parsing**: Converts natural language questions into structured intents
2. **Response Formatting**: Converts raw results into natural, conversational responses

Configure credentials:

```bash
export OPENAI_API_KEY=your_api_key
# Optional: choose a lightweight model
export OPENAI_MODEL=gpt-4o-mini
```

If no API key is set, the CLI will respond with:

```
OpenAI not configured. Set OPENAI_API_KEY to enable LLM parsing.
```

### Natural Language Response Formatting

When an OpenAI API key is configured, the system automatically formats responses into natural, conversational language:

**Without OpenAI (Raw Output):**
```
Total emails sent: 50
Total emails opened in the specified window: 1 (last week)
Total bounced emails: 6. By domain: gmail.com: 2, proton.me: 2, outlook.com: 1, yahoo.com: 1
```

**With OpenAI (Natural Language):**
```
Great question! I can see that you sent a total of 50 emails in your campaign.

Looking at the opens from last week, I found that 1 email was opened during that time period.

Regarding bounces, there were 6 emails that bounced back. The breakdown by domain shows: gmail.com had 2 bounces, proton.me had 2 bounces, outlook.com had 1 bounce, and yahoo.com had 1 bounce.
```

Time windows supported in the question:

- "last week" → Monday 00:00 to Sunday 23:59:59
- "last N days" (e.g., last 7 days)
- "since YYYY-MM-DD"
- "between YYYY-MM-DD and YYYY-MM-DD"

Examples:

```bash
python app.py "How many were opened last week?"
python app.py "How many people replied, and how quickly, last 7 days?"
python app.py "How many emails bounced, grouped by domain, between 2024-06-01 and 2024-06-30?"
```

## Schema Overview

SQLite file: `email_campaign.db`

Table `email_events`:

- `id` INTEGER PRIMARY KEY
- `email_address` TEXT NOT NULL
- `first_name` TEXT
- `last_name` TEXT
- `company` TEXT
- `subject` TEXT
- `campaign_name` TEXT NOT NULL
- `sent_at` TEXT (ISO8601) NOT NULL
- `delivered_at` TEXT (ISO8601) NULL
- `opened_at` TEXT (ISO8601) NULL
- `replied_at` TEXT (ISO8601) NULL
- `bounced` INTEGER NOT NULL DEFAULT 0

Indexes:

- `idx_email_domain` on `email_address`
- `idx_campaign_sent` on `(campaign_name, sent_at)`

## Example Q&A

```bash
$ python app.py "How many emails were sent?"
Total emails sent: 140

$ python app.py "How many were opened last week?"
Total emails opened in the specified window: 58 (last week)

$ python app.py "How many people replied, and how quickly?"
Total people who replied: 8. Average reply time: 43.9 hours

$ python app.py "How many emails bounced, grouped by domain?"
Total bounced emails: 14. By domain: gmail.com: 3, outlook.com: 3, proton.me: 3, yahoo.com: 2
```

Your results will vary on each seed run.

## Error Handling

- **Unknown/unsupported query**: Responds with guidance: try sent, opened, replied (incl. speed), bounced by domain.
- **Missing fields**: Politely states not available and lists supported metrics.
- **Ambiguous/invalid time window**: Responds with accepted formats. Defaults to no time filter if not provided.
- **Unsafe SQL**: SQL agent blocks dangerous operations (INSERT, UPDATE, DELETE, DROP, etc.) and system table access.
- **API errors**: Graceful fallback to intent-based parsing when OpenAI is unavailable.

## Assumptions & Limitations

- Only the four metrics above are supported; other fields must be added to the schema first.
- Time filters are applied against `sent_at` for simplicity.
- Average reply time is computed as `replied_at - sent_at` across reply rows.

## Advanced NLP Features

The system includes sophisticated NLP capabilities that go beyond simple regex matching:

### Time Parsing
- **Pattern-based matching** with confidence scoring
- **Comprehensive time expressions**: last week, this month, yesterday, etc.
- **Date range parsing**: between X and Y, from X to Y, since X
- **Relative time parsing**: last N days/weeks/months, N days ago
- **Robust dateutil integration** with error handling

### Query Analysis
- **Performance Metrics**: Execution time, complexity scoring, cost estimation
- **Query Caching**: LRU cache with TTL for improved performance
- **Safety Validation**: Multi-layered SQL safety checks

## Decision Log

- Product: Added `bounced` and domain grouping to surface deliverability issues at a glance.
- Product: Included `company` and `subject` to allow future segmentation without changing schema.
- Product: Implemented natural language response formatting to make data insights more accessible and conversational.
- Technical: Used SQLite for zero-config persistence and easy distribution; Pandas+Faker to quickly generate realistic mock data.
- Technical: Implemented OpenAI SQL agent for natural language to SQL conversion with comprehensive safety validation.
- Technical: Advanced NLP pipeline using pattern matching and dateutil for robust time parsing.
- Technical: Enhanced SQL safety validation blocks all mutation operations, system table access, and potentially dangerous constructs.
- Technical: Added OpenAI-powered response formatting that converts raw results into natural, conversational language.
- Performance: Added query caching, performance analysis, and optimization suggestions.

