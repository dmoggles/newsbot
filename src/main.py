# Main entry point for the News Aggregator
import logging
import argparse
import sys
from typing import List

from config_loader import load_config
from fetcher_rss import GoogleNewsFetcher
from filter import StoryFilter
from deduplicator import StoryDeduplicator
from url_decoder import URLDecoder
from article_scraper import ArticleScraper
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
                # Only update filter fields, preserve advanced fields
                existing.filter_status = story.filter_status
                existing.filter_reason = story.filter_reason
                storage.update_story(existing)
                logger.debug(f"Merged filter status into existing story: {story.story_id}")
                return 'updated', None
            else:
                logger.warning(f"Story exists but could not be loaded: {story.story_id}")
                return 'error', f"Story exists but could not be loaded: {story.story_id}"
        else:
            storage.save_story(story)
            logger.debug(f"Saved new story: {story.story_id}")
            return 'saved', None
    except Exception as e:
        error_msg = f"Failed to save story {story.story_id}: {e}"
        logger.error(error_msg)
        return 'error', error_msg

def save_stories_to_storage(storage: RedisStorage, processed_stories: List[Story]) -> tuple[int, int, int]:
    """
    Save processed stories to storage with merge logic.
    Returns (saved_count, updated_count, error_count)
    """
    saved_count = 0
    updated_count = 0
    error_count = 0
    
    for story in processed_stories:
        result, error = merge_story_with_existing(storage, story)
        if result == 'saved':
            saved_count += 1
        elif result == 'updated':
            updated_count += 1
        else:  # error
            error_count += 1
    
    return saved_count, updated_count, error_count

def setup_logging(level: str) -> None:
    """Configure logging with the specified level."""
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('newsbot.log'),
            logging.StreamHandler()
        ]
    )
    logger.info(f"Logging configured at {level.upper()} level")

def apply_url_decoding(passed_stories: List[Story], rejected_stories: List[Story]) -> tuple[List[Story], dict]:
    """
    Apply URL decoding to stories that passed filtering and need decoding.
    Returns (all_processed_stories, decode_stats)
    """
    if not passed_stories:
        logger.info("No stories passed filtering, skipping URL decoding")
        return passed_stories + rejected_stories, {"total_stories": 0, "stories_decoded": 0}
    
    logger.info(f"Starting URL decoding for {len(passed_stories)} stories that passed filtering...")
    
    url_decoder = URLDecoder()
    
    # Separate stories that need decoding from those that don't
    stories_to_decode = []
    stories_already_decoded = []
    
    for story in passed_stories:
        # Check if story needs URL decoding
        if _story_needs_url_decoding(story):
            stories_to_decode.append(story)
        else:
            # Story already has a decoded URL or doesn't need decoding
            stories_already_decoded.append(story)
    
    logger.info(f"URL decoding: {len(stories_to_decode)} stories need decoding, "
               f"{len(stories_already_decoded)} already have decoded URLs")
    
    decode_stats = {"total_stories": len(passed_stories), "stories_decoded": 0}
    
    if stories_to_decode:
        decoded_stories, decoder_stats = url_decoder.decode_stories(stories_to_decode)
        logger.info(f"URL decoding statistics: {decoder_stats}")
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
    if story.google_redirect_url and not story.url.startswith('http'):
        return True
    
    # Story has Google redirect URL and it's the same as main URL (needs decoding)
    if story.google_redirect_url and story.url == story.google_redirect_url:
        return True
    
    # Main URL is a Google News URL that needs decoding
    if 'news.google.com' in story.url and ('read/CBM' in story.url or 'articles/CBM' in story.url):
        return True
    
    return False

def main() -> None:
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='News Aggregator for BlueSky')
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level (default: INFO)'
    )
    args = parser.parse_args()
    
    # Setup logging with the specified level
    try:
        setup_logging(args.log_level)
    except ValueError as e:
        print(f"Error setting up logging: {e}", file=sys.stderr)
        return
    
    logger.info("News Aggregator starting up...")
    
    # Load config
    try:
        config = load_config()
        logger.info("Successfully loaded configuration")
        logger.debug(f"Configuration keys: {list(config.keys())}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Integrate GoogleNewsFetcher
    try:
        search_string = config.get("search_string", "Chelsea FC")
        lookback_days = config.get("lookback_days", 1)
        language = config.get("language", "en")
        
        logger.info(f"Initializing fetcher with search_string='{search_string}', lookback_days={lookback_days}, language='{language}'")
        fetcher = GoogleNewsFetcher(search_string=search_string, lookback_days=lookback_days, language=language)
        
        logger.info("Starting news fetch...")
        stories = fetcher.fetch()
        
        logger.info(f"Successfully fetched {len(stories)} stories")
        for i, story in enumerate(stories, 1):
            logger.debug(f"Story {i}: {story.title} ({story.url}) [{story.source}]")
        
        # Initialize storage first (needed for deduplication)
        storage_config = config.get("storage", {})
        redis_url = storage_config.get("redis_url", "redis://localhost:6379/0")
        
        logger.info(f"Initializing storage with Redis URL: {redis_url}")
        try:
            storage = RedisStorage(redis_url)
            logger.info("Storage initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize storage: {e}")
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
        
        logger.info(f"Deduplication complete: {len(stories)} -> {len(deduplicated_stories)} stories")
        logger.info(f"Deduplication statistics: {dedup_stats}")
        
        # Apply filtering
        story_filter = StoryFilter(config)
        
        logger.info("Starting story filtering...")
        processed_stories, filter_stats = story_filter.filter_stories(deduplicated_stories)
        
        logger.info(f"Filtering complete: All {len(processed_stories)} stories processed")
        logger.info(f"Filter statistics: {filter_stats}")
        
        # Apply URL decoding to stories that passed filtering
        passed_stories = [s for s in processed_stories if s.filter_status == "passed"]
        rejected_stories = [s for s in processed_stories if s.filter_status == "rejected"]
        
        # URL decoding logic moved to helper function
        processed_stories, decode_stats = apply_url_decoding(passed_stories, rejected_stories)
        logger.info(f"URL decoding complete: {decode_stats['stories_decoded']} stories decoded")
        
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
                delay_between_requests=delay_between_requests
            )
            
            # Scrape articles
            scraped_stories, scraping_stats = scraper.scrape_stories(passed_stories_after_decoding)
            
            # Update processed_stories with scraped content
            # Create a mapping of story_id to scraped story for efficient lookup
            scraped_story_map = {story.story_id: story for story in scraped_stories}
            
            # Update the processed_stories list with scraped content
            for i, story in enumerate(processed_stories):
                if story.story_id in scraped_story_map:
                    processed_stories[i] = scraped_story_map[story.story_id]
            
            logger.info(f"Article scraping complete: {scraping_stats['successfully_scraped']} articles scraped, "
                       f"{scraping_stats['scraping_failures']} failed, {scraping_stats['already_scraped']} already had content")
            
            if scraping_stats["scrapers_used"]:
                logger.info(f"Scrapers used: {scraping_stats['scrapers_used']}")
        else:
            logger.info("No stories passed filtering, skipping article scraping")
        
        # Save stories to storage
        if storage:
            logger.info("Saving processed stories to storage...")
            saved_count, updated_count, error_count = save_stories_to_storage(storage, processed_stories)
            
            logger.info(f"Storage complete: {saved_count} new stories saved, "
                       f"{updated_count} stories updated, {error_count} errors")
            
            # Show storage statistics
            try:
                total_stories = storage.get_story_count()
                passed_count = len(storage.get_stories_by_filter_status("passed"))
                rejected_count = len(storage.get_stories_by_filter_status("rejected"))
                
                logger.info(f"Storage statistics: {total_stories} total stories in database "
                           f"({passed_count} passed, {rejected_count} rejected)")
            except Exception as e:
                logger.warning(f"Failed to get storage statistics: {e}")
        
        # Log details about passed and rejected stories
        final_passed_stories = [s for s in processed_stories if s.filter_status == "passed"]
        final_rejected_stories = [s for s in processed_stories if s.filter_status == "rejected"]
        
        logger.info(f"Final results: {len(final_passed_stories)} stories passed, {len(final_rejected_stories)} rejected")
        
        # Log details about URL decoding for passed stories
        if final_passed_stories:
            decoded_count = sum(1 for s in final_passed_stories if s.google_redirect_url and s.url != s.google_redirect_url)
            logger.info(f"URL decoding: {decoded_count} stories have decoded URLs")
        
        for story in final_passed_stories:
            if story.google_redirect_url:
                logger.debug(f"PASSED (DECODED): {story.title} [{story.source}] - {story.filter_reason}")
                logger.debug(f"  Original: {story.google_redirect_url[:80]}...")
                logger.debug(f"  Decoded:  {story.url}")
            else:
                logger.debug(f"PASSED (DIRECT): {story.title} [{story.source}] - {story.filter_reason}")
        
        for story in final_rejected_stories:
            logger.debug(f"REJECTED: {story.title} [{story.source}] - {story.filter_reason}")
            
    except Exception as e:
        logger.error(f"Error during news processing: {e}")
        return
    
    logger.info("News Aggregator completed successfully")

if __name__ == "__main__":
    main()
