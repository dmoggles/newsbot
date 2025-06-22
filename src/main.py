# Main entry point for the News Aggregator
import logging
import argparse
import sys
from typing import List, Dict
from datetime import datetime

from config_loader import load_config
from fetcher_rss import GoogleNewsFetcher
from filter import StoryFilter
from deduplicator import StoryDeduplicator
from url_decoder import URLDecoder
from article_scraper import ArticleScraper
from summarizer import Summarizer
from relevance_checker import RelevanceChecker
from bluesky_poster import BlueSkyPoster
from storage import RedisStorage, Story

logger = logging.getLogger(__name__)


def merge_story_with_existing(storage: RedisStorage, story: Story) -> tuple[str, str | None]:
    """
    Merge a new story with existing story, preserving advanced fields.
    Returns ('saved'|'updated'|'error', error_message_or_None)
    """
    try:
        if storage.story_exists(story.story_id):
            existing = storage.get_story(story.story_id)
            if existing:
                # Only update filter fields, preserve advanced fields                existing.filter_status = story.filter_status
                existing.filter_reason = story.filter_reason
                storage.update_story(existing)
                logger.debug("Merged filter status into existing story: %s", story.story_id)
                return "updated", None
            else:
                logger.warning("Story exists but could not be loaded: %s", story.story_id)
                return "error", "Story exists but could not be loaded: %s" % story.story_id

        storage.save_story(story)
        logger.debug("Saved new story: %s", story.story_id)
        return "saved", None
    except Exception as e:
        error_msg = "Failed to save story %s: %s" % (story.story_id, e)
        logger.error("%s", error_msg)
        return "error", error_msg


def save_stories_to_storage(storage: RedisStorage, processed_stories: List[Story]) -> tuple[int, int, int]:
    """
    Save processed stories to storage with merge logic.
    Returns (saved_count, updated_count, error_count)
    """
    saved_count = 0
    updated_count = 0
    error_count = 0

    for story in processed_stories:
        result, _ = merge_story_with_existing(storage, story)
        if result == "saved":
            saved_count += 1
        elif result == "updated":
            updated_count += 1
        else:  # error
            error_count += 1

    return saved_count, updated_count, error_count


def setup_logging(level: str, log_to_file: bool = True, log_file: str = "newsbot.log") -> None:
    """
    Configure logging with the specified level and optional file output.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to write logs to a file
        log_file: Path to the log file (used only if log_to_file is True)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")  # Create handlers list
    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if log_to_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    if log_to_file:
        logger.info("Logging configured at %s level with file output to %s", level.upper(), log_file)
    else:
        logger.info("Logging configured at %s level with console output only", level.upper())


def apply_url_decoding(
    passed_stories: List[Story], rejected_stories: List[Story]
) -> tuple[List[Story], Dict[str, int]]:
    """
    Apply URL decoding to stories that passed filtering and need decoding.
    Returns (all_processed_stories, decode_stats)
    """
    if not passed_stories:
        logger.info("No stories passed filtering, skipping URL decoding")
        return passed_stories + rejected_stories, {
            "total_stories": 0,
            "stories_decoded": 0,
        }

    logger.info(
        "Starting URL decoding for %d stories that passed filtering...",
        len(passed_stories),
    )

    url_decoder = URLDecoder()

    # Separate stories that need decoding from those that don't
    stories_to_decode: List[Story] = []
    stories_already_decoded: List[Story] = []

    for story in passed_stories:
        # Check if story needs URL decoding
        if _story_needs_url_decoding(story):
            stories_to_decode.append(story)
        else:
            # Story already has a decoded URL or doesn't need decoding
            stories_already_decoded.append(story)

    logger.info(
        "URL decoding: %d stories need decoding, %d already have decoded URLs",
        len(stories_to_decode),
        len(stories_already_decoded),
    )

    decode_stats = {"total_stories": len(passed_stories), "stories_decoded": 0}

    if stories_to_decode:
        decoded_stories, decoder_stats = url_decoder.decode_stories(stories_to_decode)
        logger.info("URL decoding statistics: %s", decoder_stats)
        decode_stats["stories_decoded"] = decoder_stats.get("successfully_decoded", 0)

        # Combine decoded stories with already-decoded stories
        all_passed_stories = decoded_stories + stories_already_decoded
    else:
        all_passed_stories = stories_already_decoded
        logger.info("No stories required URL decoding")

    # Combine all stories back together (passed + rejected)
    return all_passed_stories + rejected_stories, decode_stats


def _story_needs_url_decoding(story: Story) -> bool:
    """Check if a story needs URL decoding."""
    # Story has Google redirect URL and main URL is not a proper URL
    if story.google_redirect_url and not story.url.startswith("http"):
        return True

    # Story has Google redirect URL and it's the same as main URL (needs decoding)
    if story.google_redirect_url and story.url == story.google_redirect_url:
        return True

    # Main URL is a Google News URL that needs decoding
    if "news.google.com" in story.url and ("read/CBM" in story.url or "articles/CBM" in story.url):
        return True

    return False


def main() -> None:
    """
    Main entry point for the News Aggregator for BlueSky.
    This function orchestrates the entire news aggregation pipeline, including:
    - Parsing command-line arguments for logging configuration.
    - Setting up logging.
    - Loading configuration from file or environment.
    - Fetching news stories using GoogleNewsFetcher.
    - Initializing storage (Redis) for deduplication and persistence.
    - Deduplicating fetched stories, optionally using semantic deduplication.
    - Filtering stories based on configuration rules.
    - Decoding URLs for filtered stories.
    - Scraping article content for stories that passed filtering.
    - Summarizing scraped articles using various summarization strategies (including OpenAI).
    - Checking the relevance of summarized stories.
    - Posting relevant stories to BlueSky, respecting rate limits and post history.
    - Saving processed stories to storage and updating their status.
    - Logging detailed statistics and results at each stage.
    Handles errors gracefully at each step and logs progress and issues for debugging and monitoring.
    """

    parser = argparse.ArgumentParser(description="News Aggregator for BlueSky")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level (default: INFO)",
    )
    args = parser.parse_args()

    # Setup logging with the specified level
    try:
        setup_logging(args.log_level)
    except ValueError as e:
        print(f"Error setting up logging: {e}", file=sys.stderr)
        return

    logger.info("News Aggregator starting up...")
    try:
        run_once()
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        logger.exception("Full traceback:")


def run_once() -> None:
    """
    Run the news aggregation pipeline once.
    This function is called by the main entry point to execute the entire news aggregation process.
    It includes fetching news stories, deduplicating, filtering, decoding URLs, scraping articles,
    summarizing, checking relevance, and posting to BlueSky.
    It handles all steps in a single run, logging progress and results at each stage.
    """
    # Load config
    try:
        config = load_config()
        logger.info("Successfully loaded configuration")
        logger.debug("Configuration keys: %s", list(config.keys()))
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return

    # Integrate GoogleNewsFetcher
    try:
        search_string = config.get("search_string", "Chelsea FC")
        lookback_days = config.get("lookback_days", 1)
        language = config.get("language", "en")

        logger.info(
            "Initializing fetcher with search_string='%s', lookback_days=%s, language='%s'",
            search_string,
            lookback_days,
            language,
        )
        fetcher = GoogleNewsFetcher(search_string=search_string, lookback_days=lookback_days, language=language)

        logger.info("Starting news fetch...")
        stories = fetcher.fetch()

        logger.info("Successfully fetched %d stories", len(stories))
        for i, story in enumerate(stories, 1):
            logger.debug("Story %d: %s (%s) [%s]", i, story.title, story.url, story.source)

        # Initialize storage first (needed for deduplication)
        storage_config = config.get("storage", {})
        redis_url = storage_config.get("redis_url", "redis://localhost:6379/0")

        logger.info("Initializing storage with Redis URL: %s", redis_url)
        try:
            storage = RedisStorage(redis_url)
            logger.info("Storage initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize storage: %s", e)
            logger.warning("Continuing without storage - stories will not be persisted")
            storage = None

        # Apply deduplication
        deduplicator = StoryDeduplicator()
        if storage:
            # Load existing stories for deduplication
            existing_stories = storage.get_all_stories()
            deduplicator.load_existing_stories(existing_stories)

        # Get deduplication configuration
        dedup_config = config.get("deduplication", {})
        enable_semantic = dedup_config.get("enable_semantic", False)

        logger.info("Starting story deduplication...")
        if enable_semantic:
            logger.info("Semantic deduplication is enabled (experimental)")
        deduplicated_stories, dedup_stats = deduplicator.deduplicate_stories(stories, enable_semantic=enable_semantic)

        logger.info("Deduplication complete: %d -> %d stories", len(stories), len(deduplicated_stories))
        logger.info("Deduplication statistics: %s", dedup_stats)

        # Apply filtering
        story_filter = StoryFilter(config)

        logger.info("Starting story filtering...")
        processed_stories, filter_stats = story_filter.filter_stories(deduplicated_stories)

        logger.info("Filtering complete: All %d stories processed", len(processed_stories))
        logger.info("Filter statistics: %s", filter_stats)

        # Apply URL decoding to stories that passed filtering
        passed_stories = [s for s in processed_stories if s.filter_status == "passed"]
        rejected_stories = [
            s for s in processed_stories if s.filter_status == "rejected"
        ]  # URL decoding logic moved to helper function
        processed_stories, decode_stats = apply_url_decoding(passed_stories, rejected_stories)
        logger.info("URL decoding complete: %d stories decoded", decode_stats["stories_decoded"])

        # Apply article scraping to stories that passed filtering
        passed_stories_after_decoding = [s for s in processed_stories if s.filter_status == "passed"]

        if passed_stories_after_decoding:
            logger.info("Starting article scraping...")

            # Initialize article scraper with configuration
            scraper_config = config.get("scraper", {})
            timeout = scraper_config.get("timeout", 30)
            max_retries = scraper_config.get("max_retries", 3)
            delay_between_requests = scraper_config.get("delay_between_requests", 1.0)

            scraper = ArticleScraper(
                timeout=timeout,
                max_retries=max_retries,
                delay_between_requests=delay_between_requests,
            )

            # Scrape articles
            scraped_stories, scraping_stats = scraper.scrape_stories(passed_stories_after_decoding)

            # Update processed_stories with scraped content
            # Create a mapping of story_id to scraped story for efficient lookup
            scraped_story_map = {
                story.story_id: story for story in scraped_stories
            }  # Update the processed_stories list with scraped content
            for i, story in enumerate(processed_stories):
                if story.story_id in scraped_story_map:
                    processed_stories[i] = scraped_story_map[story.story_id]

            logger.info(
                "Article scraping complete: %d articles scraped, %d failed, %d already had content",
                scraping_stats["successfully_scraped"],
                scraping_stats["scraping_failures"],
                scraping_stats["already_scraped"],
            )

            if scraping_stats["scrapers_used"]:
                logger.info("Scrapers used: %s", scraping_stats["scrapers_used"])

            # Apply summarization to scraped stories
            logger.info("Starting story summarization...")

            # Get summarizer configuration
            summarizer_config = config.get("summarizer", {})

            # Get OpenAI configuration (merged from secrets)
            openai_config = config.get("openai", {})

            # Merge configs for summarizer
            full_summarizer_config = {**summarizer_config, **openai_config}

            # Initialize summarizer
            summarizer = Summarizer(full_summarizer_config)

            # Get stories that need summarization (those that passed filtering)
            stories_to_summarize = [s for s in processed_stories if s.filter_status == "passed"]

            if stories_to_summarize:
                # Generate summaries
                summarized_stories, summary_stats = summarizer.summarize_stories(stories_to_summarize)

                # Update processed_stories with summarized content
                # Create a mapping of story_id to summarized story for efficient lookup
                summarized_story_map = {
                    story.story_id: story for story in summarized_stories
                }  # Update the processed_stories list with summarized content
                for i, story in enumerate(processed_stories):
                    if story.story_id in summarized_story_map:
                        processed_stories[i] = summarized_story_map[story.story_id]

                logger.info(
                    "Summarization complete: %d stories summarized, %d used OpenAI, %d used condensation, %d used headline fallback, %d used video prefix, %d failed",
                    summary_stats["summarized"],
                    summary_stats["used_openai"],
                    summary_stats.get("used_condensation", 0),
                    summary_stats["used_headline"],
                    summary_stats["used_video_prefix"],
                    summary_stats["failed"],
                )

                # Apply relevance checking after summarization
                logger.info("Starting relevance checking...")

                # Initialize relevance checker
                relevance_checker = RelevanceChecker(config)

                # Get source types for each story (from filter results)
                source_types: Dict[str, str] = {}
                for story in stories_to_summarize:
                    # Determine source type based on filter metadata
                    # If the story passed filtering, we need to check its source type
                    source_type = "accepted"  # Default to accepted

                    # Check if story is from confirmed source by re-running source check
                    story_filter_temp = StoryFilter(config)
                    is_allowed, detected_source_type = story_filter_temp.is_source_allowed(story.source)
                    if is_allowed and detected_source_type == "confirmed":
                        source_type = "confirmed"

                    source_types[story.story_id] = source_type

                # Check relevance
                relevance_checked_stories, relevance_stats = relevance_checker.check_stories(
                    stories_to_summarize, source_types
                )  # Update processed_stories with relevance information
                relevance_story_map = {story.story_id: story for story in relevance_checked_stories}

                for i, story in enumerate(processed_stories):
                    if story.story_id in relevance_story_map:
                        processed_stories[i] = relevance_story_map[story.story_id]

                logger.info(
                    "Relevance checking complete: %d stories checked, %d relevant, %d not relevant, %d from confirmed sources",
                    relevance_stats["total"],
                    relevance_stats["relevant"],
                    relevance_stats["not_relevant"],
                    relevance_stats["confirmed_skipped"],
                )

                if relevance_stats.get("keywords_matched"):
                    logger.info("Keywords matched: %s", relevance_stats["keywords_matched"])
            else:
                logger.info("No stories need summarization")
        else:
            logger.info("No stories passed filtering, skipping article scraping and summarization")

        # BlueSky posting
        if storage:
            logger.info("Starting BlueSky posting...")

            # Initialize BlueSky poster
            bluesky_poster = BlueSkyPoster(config)  # Get stories that are ready to be posted from storage
            postable_stories = storage.get_postable_stories()
            logger.info("Found %d stories ready for posting", len(postable_stories))

            if postable_stories:
                # Get the last successful post time from storage
                last_post_time_str = (
                    storage.get_last_successful_post_time()
                )  # Convert string timestamp back to datetime if available
                if last_post_time_str:
                    try:
                        last_post_time = datetime.fromisoformat(last_post_time_str.replace("Z", "+00:00"))
                        bluesky_poster.set_last_post_time(last_post_time)
                    except Exception as e:
                        logger.warning(
                            "Failed to parse last post time %s: %s", last_post_time_str, e
                        )  # Attempt to post stories
                posting_stats = bluesky_poster.post_stories(postable_stories)

                logger.info(
                    "BlueSky posting complete: %d stories processed, %d posted, %d failed, %d skipped, %d rate limited",
                    posting_stats["total"],
                    posting_stats["posted"],
                    posting_stats["failed"],
                    posting_stats["skipped"],
                    posting_stats["rate_limited"],
                )  # Update stories in storage with posting results
                updated_count = 0
                for story in postable_stories:
                    if story.post_status:  # Only update if post status was set
                        storage.update_story(story)
                        updated_count += 1

                if updated_count > 0:
                    logger.info("Updated %d stories with posting results", updated_count)
            else:
                logger.info("No stories ready for posting")
        else:
            logger.warning("Storage not available - skipping BlueSky posting")

        # Save stories to storage
        if storage:
            logger.info("Saving processed stories to storage...")
            saved_count, updated_count, error_count = save_stories_to_storage(storage, processed_stories)

            logger.info(
                "Storage complete: %d new stories saved, %d stories updated, %d errors",
                saved_count,
                updated_count,
                error_count,
            )

            # Show storage statistics
            try:
                total_stories = storage.get_story_count()
                passed_count = len(storage.get_stories_by_filter_status("passed"))
                rejected_count = len(storage.get_stories_by_filter_status("rejected"))

                logger.info(
                    "Storage statistics: %d total stories in database (%d passed, %d rejected)",
                    total_stories,
                    passed_count,
                    rejected_count,
                )
            except Exception as e:
                logger.warning("Failed to get storage statistics: %s", e)

        # Log details about passed and rejected stories
        final_passed_stories = [s for s in processed_stories if s.filter_status == "passed"]
        final_rejected_stories = [s for s in processed_stories if s.filter_status == "rejected"]

        logger.info(
            "Final results: %d stories passed, %d rejected", len(final_passed_stories), len(final_rejected_stories)
        )

        # Log details about URL decoding for passed stories
        if final_passed_stories:
            decoded_count = sum(
                1 for s in final_passed_stories if s.google_redirect_url and s.url != s.google_redirect_url
            )
            logger.info("URL decoding: %d stories have decoded URLs", decoded_count)

        for story in final_passed_stories:
            if story.google_redirect_url:
                logger.debug("PASSED (DECODED): %s [%s] - %s", story.title, story.source, story.filter_reason)
                logger.debug("  Original: %s...", story.google_redirect_url[:80])
                logger.debug("  Decoded:  %s", story.url)
            else:
                logger.debug("PASSED (DIRECT): %s [%s] - %s", story.title, story.source, story.filter_reason)

        for story in final_rejected_stories:
            logger.debug("REJECTED: %s [%s] - %s", story.title, story.source, story.filter_reason)

    except Exception as e:
        logger.error("Error during news processing: %s", e)
        return

    logger.info("News Aggregator completed successfully")


if __name__ == "__main__":
    main()
