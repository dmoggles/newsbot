# Main entry point for the News Aggregator
import logging
import argparse
import sys

logger = logging.getLogger(__name__)

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
    
    # Example: Load config
    try:
        from config_loader import load_config
        config = load_config()
        logger.info("Successfully loaded configuration")
        logger.debug(f"Configuration keys: {list(config.keys())}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return

    # Integrate GoogleNewsFetcher
    try:
        from fetcher import GoogleNewsFetcher
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
        from filter import StoryFilter
        story_filter = StoryFilter(config)
        
        logger.info("Starting story filtering...")
        filtered_stories, filter_stats = story_filter.filter_stories(stories)
        
        logger.info(f"Filtering complete: {len(filtered_stories)} stories passed out of {len(stories)} total")
        logger.info(f"Filter statistics: {filter_stats}")
        
        for i, story in enumerate(filtered_stories, 1):
            logger.debug(f"Filtered story {i}: {story.title} [{story.source}]")
            
    except Exception as e:
        logger.error(f"Error during news processing: {e}")
        return
    
    logger.info("News Aggregator completed successfully")

if __name__ == "__main__":
    main()
