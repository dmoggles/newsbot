# News Aggregator for BlueSky

An automated news aggregation and posting system that collects relevant news stories from Google News, filters and summarizes them, and posts high-quality updates to the BlueSky social network at a controlled rate.

## Features

✅ **Completed Components:**
- **YAML Configuration Management** - Flexible config loading with secrets support
- **Google News Fetching** - Automated story collection with customizable search parameters  
- **Redis-based Storage** - Persistent storage with Pydantic models and PostStatus tracking
- **Story Filtering System** - Source, headline, and URL filtering with status tracking
- **Advanced Deduplication** - URL and headline-based duplicate detection with semantic placeholders
- **Comprehensive Logging** - Configurable log levels with file and console output
- **Command Line Interface** - Flexible execution with argument parsing
- **Robust Testing Suite** - Comprehensive unit tests for all components

🚧 **In Development:**
- Google News URL resolution (`new_decoderv1` integration)
- Full article scraping with fallback handling
- OpenAI-powered summarization with retry logic
- Relevance checker for accepted sources
- BlueSky posting with rate limiting
- FastAPI observability endpoints

See `specs/prd.md` for complete requirements and `specs/todo.md` for current progress.

## Setup

This project uses Poetry for dependency management:

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Configure the application** by editing:
   - `configs/config.yaml` - Main configuration settings
   - `configs/secrets.yaml` - API keys and sensitive data

## Usage

Run the news aggregator with different logging levels:

```bash
# Default INFO level logging
poetry run python src/main.py

# Debug level for development
poetry run python src/main.py --log-level DEBUG

# Warning level for production
poetry run python src/main.py --log-level WARNING

# See all available options
poetry run python src/main.py --help
```

## Configuration

The application uses YAML configuration files:

- **`configs/config.yaml`** - Main settings (search terms, sources, filters)
- **`configs/secrets.yaml`** - API keys (OpenAI, BlueSky credentials)

Example configuration structure:
```yaml
fetcher:
  search_string: "Chelsea FC"
  lookback_days: 1
  language: "en"

filter:
  confirmed_sources:
    - "BBC News"
    - "Chelsea Football Club"
  accepted_sources:
    - "The Guardian"
    - "London Evening Standard"
  banned_headline_keywords:
    - "rumor"
    - "gossip"
  banned_url_keywords:
    - "clickbait"
    - "sponsored"

deduplication:
  enable_semantic: false  # Experimental NLP-based deduplication
  semantic_threshold: 0.8

storage:
  redis_url: "redis://localhost:6379/0"

rate_limit:
  post_interval_minutes: 30
```

## Project Structure

```
newsbot/
├── src/                    # Main source code
│   ├── main.py            # Application entry point with CLI
│   ├── config_loader.py   # YAML configuration management
│   ├── fetcher.py         # Google News integration
│   ├── filter.py          # Story filtering system
│   ├── deduplicator.py    # Advanced deduplication logic
│   └── storage.py         # Redis-based persistence
├── tests/                 # Test suite
│   ├── test_config_loader.py
│   ├── test_fetcher.py
│   ├── test_filter.py
│   ├── test_deduplicator.py
│   └── test_storage.py
├── configs/               # Configuration files
│   ├── config.yaml       # Main configuration
│   └── secrets.yaml      # API keys and secrets
├── docs/                  # Documentation
│   └── semantic_deduplication.md
├── specs/                 # Project specifications
│   ├── prd.md            # Product requirements
│   └── todo.md           # Development progress
└── scripts/              # Utility scripts
```

## Logging

The application provides comprehensive logging with configurable levels:

- **DEBUG** - Detailed processing information for development
- **INFO** - General application flow and status updates
- **WARNING** - Important notices and potential issues
- **ERROR** - Error conditions that don't stop execution
- **CRITICAL** - Severe errors that may cause application termination

Logs are written to both:
- `newsbot.log` - Persistent file logging
- Console output - Real-time monitoring

## Development

Run tests:
```bash
poetry run pytest
```

Check code style:
```bash
poetry run mypy src/
```

## Requirements

- Python 3.10+
- Redis (for persistent storage)
- Google News access
- OpenAI API key (for summarization)
- BlueSky account (for posting)

## Processing Pipeline

The NewsBot follows a structured pipeline for processing news stories:

### 1. **Story Fetching**
- Connects to Google News with configurable search parameters
- Fetches stories from the last N days (configurable)
- Processes raw Google News data into structured Story objects
- Generates stable story IDs using content hashing

### 2. **Deduplication**
- **Story ID matching**: Prevents exact duplicate processing
- **URL normalization**: Removes tracking parameters and handles redirects
- **Headline similarity**: Detects stories with similar titles
- **Google News handling**: Smart handling of redirect URLs
- **Batch processing**: Prevents duplicates within same fetch batch
- **Semantic placeholders**: Framework ready for future NLP-based deduplication

### 3. **Filtering**
- **Source validation**: Confirms stories from trusted sources
- **Headline filtering**: Removes stories with banned keywords
- **URL filtering**: Blocks content from unwanted domains
- **Status tracking**: Records filter decisions and reasons
- **Comprehensive logging**: Detailed filter statistics and decisions

### 4. **Storage**
- **Redis persistence**: All stories stored with full metadata
- **Filter status preservation**: Tracks passed/rejected with reasons
- **Advanced field preservation**: Protects summary, post_status during updates
- **Story lifecycle management**: Handles updates without data loss
- **Statistics tracking**: Real-time counts of passed/rejected stories

### 5. **Logging & Observability**
- **Multi-level logging**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **File and console output**: Persistent and real-time monitoring
- **Processing statistics**: Detailed metrics for each pipeline stage
- **Performance tracking**: Story counts, processing times, error rates

## Current Statistics Tracking

The application provides real-time statistics for:

- **Fetcher**: Stories retrieved, processing success rate
- **Deduplication**: Duplicates by type (story_id, URL, headline, semantic)
- **Filtering**: Pass/fail rates, source breakdown, filter reasons
- **Storage**: Total stories, new vs updated, error counts
- **Overall**: Pipeline throughput, processing times
