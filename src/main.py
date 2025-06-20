# Main entry point for the News Aggregator
import logging
import argparse
import sys
from typing import List

from config_loader import load_config
from fetcher import GoogleNewsFetcher
from filter import StoryFilter
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
        
        # Apply filtering
        story_filter = StoryFilter(config)
        
        logger.info("Starting story filtering...")
        processed_stories, filter_stats = story_filter.filter_stories(stories)
        
        logger.info(f"Filtering complete: All {len(processed_stories)} stories processed")
        logger.info(f"Filter statistics: {filter_stats}")
        
        # Initialize storage
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
        passed_stories = [s for s in processed_stories if s.filter_status == "passed"]
        rejected_stories = [s for s in processed_stories if s.filter_status == "rejected"]
        
        logger.info(f"Stories passed: {len(passed_stories)}, rejected: {len(rejected_stories)}")
        
        for story in passed_stories:
            logger.debug(f"PASSED: {story.title} [{story.source}] - {story.filter_reason}")
        
        for story in rejected_stories:
            logger.debug(f"REJECTED: {story.title} [{story.source}] - {story.filter_reason}")
            
    except Exception as e:
        logger.error(f"Error during news processing: {e}")
        return
    
    logger.info("News Aggregator completed successfully")

if __name__ == "__main__":
    main()
