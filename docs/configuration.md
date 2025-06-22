# Configuration Guide

This document provides comprehensive configuration options for the NewsBot application. The configuration is split between two YAML files:

- **`configs/config.yaml`** - Main application settings (committed to version control)
- **`configs/secrets.yaml`** - API keys and sensitive data (excluded from version control)

## Configuration Files Overview

### Main Configuration (`configs/config.yaml`)

Contains all non-sensitive application settings including fetching parameters, filtering rules, processing options, and system configuration.

### Secrets Configuration (`configs/secrets.yaml`)

Contains sensitive information like API keys, passwords, and credentials. This file should:
- **Never be committed to version control**
- Be created manually on each deployment
- Have restricted file permissions (readable only by the application user)

---

## Main Configuration Reference

### `fetcher` - News Fetching Settings

Controls how news stories are retrieved from Google News.

```yaml
fetcher:
  lookback_days: 1          # Number of days to look back for news (1-7 recommended)
  search_string: "Chelsea FC"  # Search term for Google News
  language: "en"            # Language code (en, es, fr, de, etc.)
```

**Options:**
- **`lookback_days`** (integer, 1-7): How many days back to search for news stories
  - Lower values (1-2) for frequent updates
  - Higher values (3-7) for comprehensive coverage
- **`search_string`** (string): The search query sent to Google News
  - Use specific terms for better filtering
  - Enclose phrases in quotes for exact matches
- **`language`** (string): Two-letter language code
  - Supported: `en`, `es`, `fr`, `de`, `it`, `pt`, etc.

---

### `filter` - Story Filtering Rules

Defines which stories are accepted or rejected based on source and content.

```yaml
filter:
  confirmed_sources:
    - "BBC News"
    - "Reuters"
    - "Chelsea Football Club"
  accepted_sources:
    - "The Guardian"
    - "Sky Sports"
  banned_headline_keywords:
    - "rumor"
    - "gossip"
    - "arrest"
  banned_url_keywords:
    - "clickbait"
    - "sponsored"
    - "youtube"
    - "reddit"
```

**Source Categories:**
- **`confirmed_sources`** (list): Trusted sources that bypass relevance checking
  - Stories from these sources are automatically accepted (if not banned)
  - Use for official sources and highly trusted news outlets
- **`accepted_sources`** (list): Sources that require relevance checking
  - Stories must pass both source validation and relevance checking
  - Use for general news outlets that may cover your topic

**Content Filtering:**
- **`banned_headline_keywords`** (list): Keywords that cause headline rejection
  - Case-insensitive substring matching
  - Use to filter out unwanted content types
- **`banned_url_keywords`** (list): Keywords that cause URL rejection
  - Applied to the final resolved URL
  - Use to block specific domains or content types

---

### `deduplication` - Duplicate Story Detection

Controls how duplicate stories are identified and removed.

```yaml
deduplication:
  enable_semantic: false     # Enable NLP-based semantic deduplication (experimental)
  semantic_threshold: 0.8   # Similarity threshold for semantic matching (0.0-1.0)
```

**Current Implementation:**
- **URL-based**: Removes stories with identical resolved URLs
- **Headline-based**: Removes stories with identical headlines
- **Story ID**: Prevents reprocessing of previously seen stories

**Future Enhancement:**
- **`enable_semantic`** (boolean): Enables semantic similarity detection using NLP
  - Currently experimental/not implemented
  - When enabled, will use sentence transformers for content similarity
- **`semantic_threshold`** (float, 0.0-1.0): Similarity threshold for semantic matching
  - Higher values = more strict (only very similar stories considered duplicates)
  - Lower values = more lenient (somewhat similar stories considered duplicates)

---

### `scraper` - Article Content Extraction

Configuration for scraping full article content from URLs.

```yaml
scraper:
  timeout: 30                    # HTTP request timeout in seconds
  max_retries: 3                # Maximum retry attempts for failed requests
  delay_between_requests: 1.0   # Delay between requests in seconds
```

**Options:**
- **`timeout`** (integer): Maximum time to wait for HTTP responses
  - Recommended: 20-60 seconds
  - Lower for faster processing, higher for slow sites
- **`max_retries`** (integer): Number of retry attempts for failed requests
  - Recommended: 2-5 retries
  - Helps handle temporary network issues
- **`delay_between_requests`** (float): Delay between HTTP requests
  - Helps avoid rate limiting and reduces server load
  - Recommended: 0.5-2.0 seconds

**Scraping Methods:**
The scraper uses multiple extraction strategies in order:
1. **newspaper3k** - General news article extraction
2. **trafilatura** - Advanced content extraction
3. **BeautifulSoup** - Fallback HTML parsing

---

### `summarizer` - Story Summarization

Controls how articles are summarized for posting.

```yaml
summarizer:
  max_length: 300      # Maximum summary length in characters
  retry_count: 5       # Number of retries if summary exceeds max_length
```

**Options:**
- **`max_length`** (integer): Maximum allowed summary length
  - BlueSky character limit consideration
  - Recommended: 250-300 characters to leave room for source links
- **`retry_count`** (integer): Retries for over-length summaries
  - OpenAI summaries that exceed max_length are retried with stricter prompts
  - Recommended: 3-7 retries

**Summarization Strategies:**
1. **OpenAI** (preferred): Uses GPT models for intelligent summarization
2. **Condensation**: Extracts key sentences from article content
3. **Headline**: Falls back to using the original headline
4. **Video Prefix**: Special handling for video content

---

### `openai` - OpenAI API Configuration

Configuration for OpenAI GPT models used in summarization.

```yaml
openai:
  model: "gpt-4o-mini"        # GPT model to use for summarization
  max_tokens: 150             # Maximum tokens per API request
  temperature: 0.3            # Creativity level (0.0-1.0)
```

**Options:**
- **`model`** (string): GPT model to use for summarization
  - **`"gpt-4o-mini"`**: Cost-effective, good quality (recommended)
  - **`"gpt-4o"`**: Higher quality, more expensive
  - **`"gpt-3.5-turbo"`**: Faster, lower cost, decent quality
- **`max_tokens`** (integer): Maximum tokens per API request
  - Recommended: 100-200 for summaries
  - Higher values allow longer summaries but cost more
- **`temperature`** (float, 0.0-1.0): Controls creativity/randomness
  - **0.0-0.3**: More focused, consistent summaries (recommended)
  - **0.4-0.7**: Balanced creativity and consistency
  - **0.8-1.0**: More creative, varied output

**Note:** The API key is configured separately in `secrets.yaml` for security.

---

### `rate_limit` - Posting Rate Control

Controls the frequency of posts to avoid spamming.

```yaml
rate_limit:
  post_interval_minutes: 30   # Minimum minutes between posts
```

**Options:**
- **`post_interval_minutes`** (integer): Minimum time between BlueSky posts
  - Recommended: 15-60 minutes depending on your audience
  - Higher values for less frequent, more curated posting
  - Lower values for more active news coverage

---

### `relevance_checker` - Content Relevance Validation

Determines if stories from accepted sources are relevant to your topic.

```yaml
relevance_checker:
  keywords:
    - "Chelsea"
    - "football"
  strategy: "substring"     # Matching strategy: "substring" or "openai"
```

**Options:**
- **`keywords`** (list): Keywords that indicate story relevance
  - Used for stories from `accepted_sources`
  - Case-insensitive matching
- **`strategy`** (string): Relevance checking method
  - **`"substring"`**: Simple keyword matching in content
  - **`"openai"`**: AI-powered relevance analysis (future enhancement)

---

### `storage` - Data Persistence

Configuration for story storage and persistence.

```yaml
storage:
  backend: "redis"                      # Storage backend type
  redis_url: "redis://localhost:6379/0"  # Redis connection string
```

**Options:**
- **`backend`** (string): Storage system type
  - Currently only `"redis"` is supported
  - Future options may include PostgreSQL, SQLite
- **`redis_url`** (string): Redis connection URL
  - Format: `redis://[username:password@]host:port/database`
  - Default database 0 is typically fine for single applications

---

## Secrets Configuration Reference

### Required Secrets File (`configs/secrets.yaml`)

Create this file manually with your API keys and credentials:

```yaml
# BlueSky Social Network Credentials
bluesky:
  handle: "your-handle.bsky.social"    # Your BlueSky handle
  app_password: "your-app-password"    # App-specific password (not your main password)

# OpenAI API Configuration
openai:
  api_key: "sk-your-openai-api-key"    # OpenAI API key
  model: "gpt-4o-mini"                 # Optional: Model to use (default: gpt-4o-mini)
  max_tokens: 150                      # Optional: Maximum tokens per request
```

### BlueSky Configuration

**Required for posting functionality:**
- **`handle`** (string): Your complete BlueSky handle including domain
  - Format: `username.bsky.social` or custom domain
  - Example: `newsbot.bsky.social`
- **`app_password`** (string): App-specific password
  - **Not your main BlueSky password**
  - Generate in BlueSky Settings → App Passwords
  - Provides limited scope access for applications

**Creating a BlueSky App Password:**
1. Log into BlueSky web interface
2. Go to Settings → App Passwords
3. Click "Add App Password"
4. Give it a descriptive name (e.g., "NewsBot")
5. Copy the generated password to your secrets file

### OpenAI Configuration

**Required for AI-powered summarization:**
- **`api_key`** (string): Your OpenAI API key
  - Get from [OpenAI API Dashboard](https://platform.openai.com/api-keys)
  - Format: `sk-...` followed by random characters
  - **This is the only required field in secrets.yaml**

**Optional overrides in secrets.yaml:**
- **`model`** (string): Override the model specified in config.yaml
- **`max_tokens`** (integer): Override the max_tokens from config.yaml
- **`temperature`** (float): Override the temperature from config.yaml

```yaml
# Minimal secrets.yaml for OpenAI
openai:
  api_key: "sk-your-openai-api-key"

# Optional: Override config.yaml settings
openai:
  api_key: "sk-your-openai-api-key"
  model: "gpt-4o"              # Override model for this deployment
  max_tokens: 200              # Override max_tokens for this deployment
```

**Configuration Precedence:**
1. Values in `secrets.yaml` override values in `config.yaml`
2. Non-sensitive settings (model, max_tokens, temperature) should generally be in `config.yaml`
3. Only put overrides in `secrets.yaml` when needed for specific deployments

---

## Security Best Practices

### File Permissions
```bash
# Set restrictive permissions on secrets file
chmod 600 configs/secrets.yaml

# Ensure config directory is not world-readable
chmod 755 configs/
```

### Environment Variables
You can override secrets using environment variables:
```bash
export NEWSBOT_OPENAI_API_KEY="your-api-key"
export NEWSBOT_BLUESKY_HANDLE="your-handle.bsky.social"
export NEWSBOT_BLUESKY_PASSWORD="your-app-password"
```

### Version Control
Ensure `secrets.yaml` is in your `.gitignore`:
```gitignore
configs/secrets.yaml
*.log
```

---

## Configuration Validation

The application validates configuration on startup:
- **Required fields**: Checks for mandatory configuration values
- **Type validation**: Ensures values are correct types (strings, integers, lists)
- **Range validation**: Validates numeric ranges where applicable
- **API connectivity**: Tests external service connections during startup

### Common Configuration Errors

1. **Missing secrets.yaml**: Create the file with required API keys
2. **Invalid Redis URL**: Ensure Redis is running and URL is correct
3. **Invalid API keys**: Verify OpenAI and BlueSky credentials
4. **Empty source lists**: Ensure at least one confirmed or accepted source
5. **Invalid time intervals**: Use positive integers for timing values

---

## Configuration Examples

### High-Frequency News Bot
```yaml
fetcher:
  lookback_days: 1
  search_string: "breaking news technology"

rate_limit:
  post_interval_minutes: 15

scraper:
  delay_between_requests: 0.5
```

### Conservative Curation Bot
```yaml
fetcher:
  lookback_days: 7
  search_string: "artificial intelligence research"

filter:
  confirmed_sources:
    - "Nature"
    - "Science"
    - "IEEE"
  banned_headline_keywords:
    - "rumor"
    - "speculation"
    - "might"
    - "could"

rate_limit:
  post_interval_minutes: 120  # 2 hours between posts
```

### Development/Testing Configuration
```yaml
fetcher:
  lookback_days: 1
  search_string: "test news"

filter:
  confirmed_sources:
    - "Test Source"
  accepted_sources: []

rate_limit:
  post_interval_minutes: 1  # Fast posting for testing

storage:
  redis_url: "redis://localhost:6379/1"  # Use database 1 for testing
```

---

For more information about specific components, see the main [README.md](../README.md) and individual module documentation.
