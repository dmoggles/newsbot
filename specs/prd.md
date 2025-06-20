# 🗞️ PRD: Automated News Aggregator for BlueSky

## 1. **Overview**
The goal of this project is to build a single-threaded, persistent news aggregation and posting system that collects relevant news stories from Google News, filters and summarizes them, and posts high-quality updates to the BlueSky social network at a controlled rate.

---

## 2. **Goals**
- Fetch news stories from Google News with customizable parameters.
- Filter stories by trusted source, banned headline/URL keywords.
- Deduplicate repeated stories using URL and headline hash.
- Summarize stories and post them to BlueSky, respecting platform character limits.
- Persist all seen and posted stories.
- Enforce a configurable rate limit to avoid timeline spamming.

---

## 3. **Non-goals**
- Multi-topic or multi-threaded execution.
- Real-time or high-throughput processing.
- Rich NLP-based content understanding (may be added later).
- Distributed execution or scaling.

---

## 4. **Functional Requirements**

### 4.1 Fetching Stories
- Use `GoogleNews` Python library.
- Configurable:
  - Look-back window (e.g., 1 day, 7 days).
  - Search string (e.g., "Chelsea FC").
  - Language set to English.
- Store metadata (title, URL, date, source, byline).

### 4.2 Filtering
- Discard stories if:
  - Source not in `confirmed_sources` or `accepted_sources`.
  - Headline matches any banned keywords (substring match).
  - URL contains any banned substrings (after resolving via `new_decoderv1`).
- Confirmed sources skip relevance checks.
- Accepted sources require additional topic relevance checks.

### 4.3 Deduplication
- Store seen stories using:
  - URL hash
  - Headline hash
- Future extensibility for NLP-based duplication detection.

### 4.4 URL Decoding
- Use `googlenewsdecoder.new_decoderv1` to convert Google redirect URLs to real article URLs.

### 4.5 Full Text Extraction
- Download resolved URL.
- Extract story text using boilerplate removal (e.g., Newspaper3k, Readability, or custom scraper).
- Normalize text to English Unicode.
- If language detected ≠ English, translate to English (via OpenAI or other configurable backend).

### 4.6 Summary Generation
- Strategy:
  - If full text is empty: summary = headline.
  - If “video” in URL: summary = `"Video: " + headline`.
  - Else: summarize via OpenAI API.
- Summary must:
  - Be ≤ 300 characters.
  - Include byline: `" By [name]."` if available.
  - Include source link: `
([media name]({url}))` (only `media name` counts toward character limit).
- If OpenAI result exceeds the character limit:
  - Retry summarization up to a configurable number of times with emphasis on brevity.
  - If still over the limit after all retries, fallback to headline as summary.
- If OpenAI call fails entirely, fallback to headline.

### 4.7 Local Storage
- Use persistent Redis or pluggable backend (abstracted via storage interface).
- Must store:
  - Raw story metadata.
  - Decoded URL.
  - Full text.
  - Summary.
  - Post status (e.g., posted, failed, skipped).

### 4.8 Posting to BlueSky
- Use `blueskysocial` Python library.
- Configurable account credentials via secrets file or YAML.
- If post successful, store timestamp and mark as posted.

### 4.9 Rate Limiting
- Configurable `post_interval_minutes`.
- Only allow one *successful* post per interval.
- Failed posts do **not** count against the cooldown.

### 4.10 Relevance Check (for non-confirmed sources)
- After generating the summary, verify topic relevance **only if the source is not confirmed**.
- Default strategy: check if a configured keyword appears in the summary (case-insensitive substring match).
- If the relevance check fails, discard the story.
- System should be extensible for future strategies (NER, embeddings, classifier, etc.).

---

## 5. **System Components**

| Component           | Responsibility                                     |
|--------------------|----------------------------------------------------|
| `fetcher`          | Uses GoogleNews to retrieve story list            |
| `filter`           | Applies headline, source, and URL filters         |
| `deduper`          | Detects duplicate stories via hash lookup         |
| `url_resolver`     | Converts Google links to actual URLs              |
| `scraper`          | Retrieves and parses full story text              |
| `summarizer`       | Builds final summary using OpenAI + logic         |
| `poster`           | Posts to BlueSky with rate limit checks           |
| `store`            | Manages Redis-backed persistent storage           |
| `config`           | Loads YAML configuration                          |
| `relevance_checker`| Validates relevance for non-confirmed sources     |

---

## 6. **Configuration (YAML Example)**
```yaml
search_string: "Chelsea FC"
lookback_days: 2
language: "en"
confirmed_sources:
  - chelseafc.com
accepted_sources:
  - bbc.co.uk
  - skysports.com
banned_headline_keywords:
  - rumor
  - arrest
  - gossip
banned_url_keywords:
  - youtube
  - reddit
relevance:
  keyword: "Chelsea"
  min_strategy: "keyword"
post_interval_minutes: 30
max_summary_regenerations: 2
bluesky:
  handle: your_bsky_handle
  app_password: your_bsky_app_password
openai:
  api_key: your_openai_api_key
```

---

## 7. **Posting Constraints**
- Summary string (headline or generated) must:
  - Fit within 300 characters.
  - Include byline and link.
  - Retry summarization before truncating.

---

## 8. **Error Handling**

| Stage                | Fallback / Action                         |
|---------------------|-------------------------------------------|
| URL not decodable   | Mark as failed, skip                      |
| Story text missing  | Use headline only                         |
| OpenAI failure      | Use headline only                         |
| Over 300 characters | Retry summarization, then fallback        |
| Post failure        | Mark as failed, retryable later           |

---

## 9. **Future Extensions**
- NLP-based relevance and deduplication.
- Topic-specific BlueSky accounts.
- Multi-threaded/concurrent scraping/posting.
- CLI or web dashboard for story review.
