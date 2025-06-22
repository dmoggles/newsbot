# ✅ TODO: News Aggregator for BlueSky

## Core Development Tasks

- [x] Set up project structure and Python environment
- [x] Implement YAML configuration loader
- [x] Implement persistent Redis-based storage abstraction (with Pydantic Story model and PostStatus enum)
- [x] Implement Google News fetcher using `GoogleNews` library
- [x] Implement source, headline, and URL filters
- [x] Integrate storage into main workflow with filtering status tracking
- [x] Implement deduplication using URL and headline hashes
- [x] Add placeholder for future NLP-based deduplication
- [x] Integrate `new_decoderv1` to resolve Google News URLs
- [x] Implement full article scraper with fallback handling
- [x] Add ScrapingStatus enum and detailed error tracking per scraping method
- [x] Enhance article scraper with aggressive extraction strategies
- [x] Create utility scripts for Redis management (flush_redis.py, check_redis.py)
- [x] Create story inspection scripts (list_stories.py, show_story.py)
- [x] Create targeted story flushing script (flush_story.py) for selective testing
- [x] Implement translation logic (optional/fallback) - SKIPPED per user request
- [x] Implement summary generator with OpenAI integration
- [x] Add logic to retry summarization if over 300 chars
- [x] Integrate summarizer into main pipeline with proper character counting
- [x] Fix Markdown formatting for source links [source](url)
- [x] Enhanced list_stories.py with summary columns and character counting
- [x] Implement relevance checker for accepted sources
- [x] Implement BlueSky poster with post tracking
- [x] Enforce rate-limiting logic
- [ ] Add fallback logic for summary and post failures
- [ ] Implement observability layer using FastAPI with endpoints for:
- [ ] Summary of all processed news stories
- [ ] Detailed inspection of individual story processing flow

## Infrastructure / Deployment

- [ ] Set up Redis instance
- [x] Create and secure configuration and secrets YAML files
- [x] Add logging and error tracking

## Testing

- [x] Add test cases for storage (save, get, update, exists, list)
- [x] Add test cases for filtering and deduplication
- [x] Add test cases for article scraping with enhanced error handling
- [x] Add test case for summary generation and fallback
- [x] Updated all tests to use proper Markdown formatting
- [x] Add test for posting logic and rate limiting
