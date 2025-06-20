# ✅ TODO: News Aggregator for BlueSky

## Core Development Tasks

- [x] Set up project structure and Python environment
- [x] Implement YAML configuration loader
- [x] Implement persistent Redis-based storage abstraction (with Pydantic Story model and PostStatus enum)
- [x] Implement Google News fetcher using `GoogleNews` library
- [ ] Implement source, headline, and URL filters
- [ ] Implement deduplication using URL and headline hashes
- [ ] Add placeholder for future NLP-based deduplication
- [ ] Integrate `new_decoderv1` to resolve Google News URLs
- [ ] Implement full article scraper with fallback handling
- [ ] Implement translation logic (optional/fallback)
- [ ] Implement summary generator with OpenAI integration
- [ ] Add logic to retry summarization if over 300 chars
- [ ] Implement relevance checker for accepted sources
- [ ] Implement BlueSky poster with post tracking
- [ ] Enforce rate-limiting logic
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
- [ ] Add test cases for filtering and deduplication
- [ ] Add test case for summary generation and fallback
- [ ] Add test for posting logic and rate limiting
