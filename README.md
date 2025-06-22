# News Aggregator for BlueSky

An automated news aggregation and posting system that collects relevant news stories from Google News, filters and summarizes them using OpenAI, and posts high-quality updates to the BlueSky social network at a controlled rate.

## 🚀 Features

### ✅ **Fully Implemented:**
- **YAML Configuration Management** - Flexible config loading with secrets support
- **Google News Fetching** - Automated story collection with customizable search parameters
- **Redis-based Storage** - Persistent storage with Pydantic models and PostStatus tracking
- **Advanced Story Filtering** - Source validation, headline/URL keyword filtering with detailed status tracking
- **Smart Deduplication** - URL and headline-based duplicate detection with semantic framework
- **Google News URL Decoding** - Resolves Google News redirect URLs to original sources
- **Full Article Scraping** - Multi-strategy content extraction with fallback handling
- **OpenAI-Powered Summarization** - Intelligent story summarization with retry logic and character limits
- **Relevance Checking** - Content relevance validation for accepted sources
- **BlueSky Integration** - Automated posting with rate limiting and post history tracking
- **Continuous Operation** - Background runner with configurable intervals and graceful shutdown
- **Comprehensive Logging** - Multi-level logging with file and console output
- **Utility Scripts** - Redis management, story inspection, and startup scripts
- **Robust Testing Suite** - Complete unit test coverage for all components

### 🔄 **Planned:**
- **FastAPI Observability Layer** - Web dashboard for monitoring and story inspection
- **Enhanced NLP Features** - Semantic deduplication and advanced content analysis

See `specs/prd.md` for complete requirements and `specs/todo.md` for development progress.

## 📋 Requirements

- Python 3.10+
- Redis (for persistent storage)
- OpenAI API key (for summarization)
- BlueSky account (for posting)

## 🛠️ Setup

This project uses Poetry for dependency management:

1. **Install Poetry** (if not already installed):
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

2. **Install dependencies**:
   ```bash
   poetry install
   ```

3. **Configure the application**:
   - Edit `configs/config.yaml` for main settings (search terms, sources, etc.)
   - Create `configs/secrets.yaml` from the example template for API keys

   ```bash
   # Copy the example secrets file and customize it
   cp configs/secrets.yaml.example configs/secrets.yaml
   # Edit with your actual API keys
   vim configs/secrets.yaml
   ```

4. **Start Redis** (required for storage):
   ```bash
   # Windows
   ./scripts/start-redis.ps1

   # Linux/macOS
   ./scripts/check_and_start_redis.sh
   ```

## 🚀 Quick Start

### Single Run
```bash
# Run once with default settings
poetry run python src/main.py

# Run with debug logging
poetry run python src/main.py --log-level DEBUG

# See all options
poetry run python src/main.py --help
```

### Continuous Operation
```bash
# Windows
./scripts/start_newsbot.bat

# Linux/macOS
./scripts/start_newsbot.sh

# Custom continuous run
poetry run python continuous_runner.py --interval 30m --log-level INFO
```

## ⚙️ Configuration

The application uses two YAML configuration files:

- **`configs/config.yaml`** - Main application settings (search terms, filtering rules, processing options)
- **`configs/secrets.yaml`** - API keys and credentials (excluded from version control)

### Quick Configuration Setup

1. **Copy and customize the main config:**
   ```bash
   # The config.yaml file contains all application settings
   # Edit search terms, sources, and processing options
   vim configs/config.yaml
   ```

2. **Create your secrets file:**
   ```bash
   # Create secrets.yaml with your API keys
   cp configs/secrets.yaml.example configs/secrets.yaml
   vim configs/secrets.yaml
   ```

3. **Add your credentials to secrets.yaml:**
   ```yaml
   # BlueSky credentials
   bluesky:
     handle: "your-handle.bsky.social"
     app_password: "your-app-password"  # Generate in BlueSky Settings

   # OpenAI API key (model settings are in config.yaml)
   openai:
     api_key: "sk-your-openai-api-key"
   ```

### 📖 Complete Configuration Reference

For comprehensive configuration documentation including all options, examples, and security best practices, see:

**[📋 Configuration Guide](docs/configuration.md)**

The configuration guide covers:
- **All configuration options** with detailed explanations
- **Security best practices** for managing secrets
- **Example configurations** for different use cases
- **Troubleshooting** common configuration issues
- **Environment variable overrides** for deployment

## 📁 Project Structure

```
newsbot/
├── src/                           # Main source code
│   ├── main.py                   # Application entry point with CLI
│   ├── config_loader.py          # YAML configuration management
│   ├── fetcher_rss.py           # Google News integration
│   ├── filter.py                # Story filtering system
│   ├── deduplicator.py          # Advanced deduplication logic
│   ├── url_decoder.py           # Google News URL resolution
│   ├── article_scraper.py       # Multi-strategy content extraction
│   ├── summarizer.py            # OpenAI-powered summarization
│   ├── relevance_checker.py     # Content relevance validation
│   ├── bluesky_poster.py        # BlueSky social posting
│   ├── storage.py               # Redis-based persistence
│   └── typechecking.py          # Type definitions and enums
├── tests/                        # Comprehensive test suite
│   ├── test_*.py                # Unit tests for all components
│   └── conftest.py              # Test configuration and fixtures
├── scripts/                      # Utility and startup scripts
│   ├── start_newsbot.bat        # Windows startup script
│   ├── start_newsbot.sh         # Linux/macOS startup script
│   ├── start-redis.ps1          # Windows Redis startup
│   └── check_and_start_redis.sh # Linux Redis management
├── configs/                      # Configuration files
│   ├── config.yaml              # Main configuration
│   └── secrets.yaml             # API keys and secrets
├── docs/                         # Documentation
│   ├── configuration.md         # Comprehensive configuration guide
│   ├── continuous_runner.md     # Continuous operation guide
│   └── semantic_deduplication.md# Future NLP features
├── specs/                        # Project specifications
│   ├── prd.md                   # Product requirements document
│   └── todo.md                  # Development progress tracking
├── stubs/                        # Type stubs for external libraries
├── continuous_runner.py         # Continuous operation script
├── *.py                         # Utility scripts (Redis, story management)
└── pyproject.toml               # Poetry configuration and dependencies
```

## 🔄 Processing Pipeline

The NewsBot follows a structured pipeline for processing news stories:

### 1. **Story Fetching** (`fetcher_rss.py`)
- Connects to Google News with configurable search parameters
- Fetches stories from the last N days (configurable)
- Processes raw Google News data into structured Story objects
- Generates stable story IDs using content hashing

### 2. **Deduplication** (`deduplicator.py`)
- **Story ID matching**: Prevents exact duplicate processing
- **URL normalization**: Removes tracking parameters and handles redirects
- **Headline similarity**: Detects stories with similar titles
- **Google News handling**: Smart handling of redirect URLs
- **Batch processing**: Prevents duplicates within same fetch batch
- **Semantic framework**: Ready for future NLP-based deduplication

### 3. **Filtering** (`filter.py`)
- **Source validation**: Confirms stories from trusted sources
- **Headline filtering**: Removes stories with banned keywords
- **URL filtering**: Blocks content from unwanted domains
- **Status tracking**: Records filter decisions and reasons
- **Comprehensive logging**: Detailed filter statistics and decisions

### 4. **URL Decoding** (`url_decoder.py`)
- **Google News resolution**: Converts redirect URLs to original sources
- **Batch processing**: Efficient handling of multiple URLs
- **Error handling**: Graceful fallback for failed resolutions
- **Statistics tracking**: Success/failure metrics

### 5. **Article Scraping** (`article_scraper.py`)
- **Multi-strategy extraction**: newspaper3k, trafilatura, BeautifulSoup
- **Fallback handling**: Tries multiple methods for maximum success
- **Content validation**: Ensures meaningful article content
- **Rate limiting**: Configurable delays between requests
- **Error tracking**: Detailed failure analysis per scraping method

### 6. **Summarization** (`summarizer.py`)
- **OpenAI integration**: GPT-powered intelligent summarization
- **Multiple strategies**: OpenAI, condensation, headline fallback
- **Character limits**: Respects BlueSky post length requirements
- **Retry logic**: Automatic retry for over-length summaries
- **Quality validation**: Ensures summary relevance and readability

### 7. **Relevance Checking** (`relevance_checker.py`)
- **Content analysis**: Validates story relevance for accepted sources
- **Keyword matching**: Configurable relevance criteria
- **Source-based logic**: Different rules for confirmed vs accepted sources
- **Decision tracking**: Logs relevance decisions and criteria

### 8. **BlueSky Posting** (`bluesky_poster.py`)
- **Rate limiting**: Configurable intervals between posts
- **Post history**: Tracks successful and failed posts
- **Authentication**: Secure BlueSky API integration
- **Status tracking**: Updates story records with posting results
- **Error handling**: Graceful handling of API failures

### 9. **Storage** (`storage.py`)
- **Redis persistence**: All stories stored with full metadata
- **Filter status preservation**: Tracks passed/rejected with reasons
- **Advanced field preservation**: Protects summary, post_status during updates
- **Story lifecycle management**: Handles updates without data loss
- **Statistics tracking**: Real-time counts of passed/rejected stories

## 🔧 Utility Scripts

### Story Management
- **`list_stories.py`** - List and filter stored stories with detailed information
- **`show_story.py`** - Display complete details for specific stories
- **`flush_story.py`** - Remove specific stories for testing
- **`flush_redis.py`** - Clear all Redis data
- **`check_redis.py`** - Verify Redis connectivity and data

### Continuous Operation
- **`continuous_runner.py`** - Run the pipeline continuously with configurable intervals
- **`scripts/start_newsbot.bat`** - Windows startup script (1-minute intervals)
- **`scripts/start_newsbot.sh`** - Linux/macOS startup script (1-minute intervals)

### Redis Management
- **`scripts/start-redis.ps1`** - Start Redis on Windows
- **`scripts/check_and_start_redis.sh`** - Check and start Redis on Linux/macOS

## 📊 Logging & Monitoring

The application provides comprehensive logging with configurable levels:

- **DEBUG** - Detailed processing information for development
- **INFO** - General application flow and status updates (default)
- **WARNING** - Important notices and potential issues
- **ERROR** - Error conditions that don't stop execution
- **CRITICAL** - Severe errors that may cause application termination

### Log Outputs
- **File logging**: `newsbot.log` (persistent, rotated)
- **Console output**: Real-time monitoring with colors
- **Configurable**: Can disable file logging for console-only operation

### Statistics Tracking
Real-time statistics for each pipeline stage:
- **Fetcher**: Stories retrieved, processing success rate
- **Deduplication**: Duplicates by type (story_id, URL, headline, semantic)
- **Filtering**: Pass/fail rates, source breakdown, filter reasons
- **URL Decoding**: Success/failure rates, processing times
- **Article Scraping**: Success by method, content quality metrics
- **Summarization**: Strategy usage, character counts, retry rates
- **Relevance Checking**: Relevance decisions, keyword matches
- **BlueSky Posting**: Post success/failure, rate limiting effectiveness
- **Storage**: Total stories, new vs updated, error counts
- **Overall**: Pipeline throughput, processing times, error rates

## 🧪 Development

### Run Tests
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test file
poetry run pytest tests/test_storage.py -v
```

### Code Quality
```bash
# Type checking
poetry run mypy src/

# Linting (if configured)
poetry run ruff check src/
```

### Development Tips
- Use `--log-level DEBUG` for detailed debugging information
- Test individual components with their respective utility scripts
- Monitor `newsbot.log` for persistent logging during development
- Use `flush_redis.py` to reset state between testing sessions

## 🔮 Future Enhancements

### Planned Features (see `specs/todo.md`)
- **FastAPI Observability Layer**: Web dashboard for monitoring and story inspection
- **Enhanced NLP**: Semantic deduplication using sentence transformers
- **Multi-source Support**: Extend beyond Google News to RSS feeds and other sources
- **Advanced Filtering**: ML-based content quality scoring
- **Performance Optimization**: Async processing and batch operations

### Configuration Extensions
- **Multiple Topics**: Support for different search terms and posting accounts
- **Scheduling**: Time-based posting schedules and content calendars
- **Content Templates**: Customizable post formatting and templates
- **Integration Webhooks**: Notifications and external system integration

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
