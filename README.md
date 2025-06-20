# News Aggregator for BlueSky

An automated news aggregation and posting system that collects relevant news stories from Google News, filters and summarizes them, and posts high-quality updates to the BlueSky social network at a controlled rate.

## Features

✅ **Completed Components:**
- **YAML Configuration Management** - Flexible config loading with secrets support
- **Google News Fetching** - Automated story collection with customizable search parameters
- **Redis-based Storage** - Persistent storage with Pydantic models and PostStatus tracking
- **Comprehensive Logging** - Configurable log levels with file and console output
- **Command Line Interface** - Flexible execution with argument parsing

🚧 **In Development:**
- Source and headline filtering
- URL deduplication and NLP-based deduplication
- Google News URL resolution
- Full article scraping with fallback handling
- OpenAI-powered summarization
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
    - chelseafc.com
  accepted_sources:
    - bbc.co.uk
    - skysports.com
  banned_headline_keywords:
    - rumor
    - gossip

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
│   └── storage.py         # Redis-based persistence
├── tests/                 # Test suite
├── configs/               # Configuration files
│   ├── config.yaml       # Main configuration
│   └── secrets.yaml      # API keys and secrets
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
