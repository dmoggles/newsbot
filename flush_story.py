#!/usr/bin/env python3
"""
Utility script to flush specific stories from Redis storage.
Allows targeted removal of stories by story ID pattern or specific ID.
"""

import argparse
import logging
import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_loader import load_config
from storage import RedisStorage

# Configure logging for this script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def flush_story_by_id(storage: RedisStorage, story_id: str) -> bool:
    """
    Remove a specific story by its exact story ID.
    
    Args:
        storage: RedisStorage instance
        story_id: Exact story ID to remove
    
    Returns:
        True if story was found and removed, False otherwise
    """
    try:
        if storage.story_exists(story_id):
            # Get story details before deletion for logging
            story = storage.get_story(story_id)
            if story:
                logger.info(f"Found story: {story.title[:60]}... [{story.source}]")
            
            # Delete the story
            success = storage.delete_story(story_id)
            if success:
                logger.info(f"Successfully deleted story: {story_id}")
                return True
            else:
                logger.error(f"Failed to delete story: {story_id}")
                return False
        else:
            logger.warning(f"Story not found: {story_id}")
            return False
    except Exception as e:
        logger.error(f"Error deleting story {story_id}: {e}")
        return False


def flush_stories_by_pattern(storage: RedisStorage, pattern: str) -> int:
    """
    Remove stories whose IDs match a pattern.
    
    Args:
        storage: RedisStorage instance
        pattern: Pattern to match against story IDs (substring match)
    
    Returns:
        Number of stories deleted
    """
    try:
        # Get all stories
        all_stories = storage.get_all_stories()
        logger.info(f"Found {len(all_stories)} total stories in database")
        
        # Find matching stories
        matching_stories = [
            story for story in all_stories 
            if pattern.lower() in story.story_id.lower()
        ]
        
        if not matching_stories:
            logger.info(f"No stories found matching pattern: '{pattern}'")
            return 0
        
        logger.info(f"Found {len(matching_stories)} stories matching pattern: '{pattern}'")
        
        # Show matching stories before deletion
        for i, story in enumerate(matching_stories, 1):
            logger.info(f"  {i}. [{story.story_id}] {story.title[:50]}... [{story.source}]")
        
        # Confirm deletion
        if len(matching_stories) > 1:
            response = input(f"\nDelete {len(matching_stories)} stories? (y/N): ").strip().lower()
            if response != 'y':
                logger.info("Deletion cancelled by user")
                return 0
        
        # Delete matching stories
        deleted_count = 0
        for story in matching_stories:
            if storage.delete_story(story.story_id):
                deleted_count += 1
                logger.debug(f"Deleted: {story.story_id}")
            else:
                logger.error(f"Failed to delete: {story.story_id}")
        
        logger.info(f"Successfully deleted {deleted_count} stories")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Error deleting stories by pattern '{pattern}': {e}")
        return 0


def list_recent_stories(storage: RedisStorage, limit: int = 10) -> None:
    """
    List recent stories to help identify which ones to delete.
    
    Args:
        storage: RedisStorage instance
        limit: Maximum number of stories to show
    """
    try:
        all_stories = storage.get_all_stories()
        
        if not all_stories:
            logger.info("No stories found in database")
            return
        
        # Sort by date (most recent first)
        # Note: This is a simple sort by story_id which contains timestamp
        sorted_stories = sorted(all_stories, key=lambda s: s.story_id, reverse=True)
        
        logger.info(f"Showing {min(limit, len(sorted_stories))} most recent stories:")
        logger.info("-" * 80)
        
        for i, story in enumerate(sorted_stories[:limit], 1):
            status_emoji = "✅" if story.filter_status == "passed" else "❌"
            scraping_info = ""
            if hasattr(story, 'scraping_status') and story.scraping_status:
                scraping_info = f" [scraping: {story.scraping_status}]"
            summary_info = ""
            if story.summary:
                summary_info = f" [summary: {len(story.summary)} chars]"
            
            logger.info(f"{i:2d}. {status_emoji} [{story.story_id}]")
            logger.info(f"     {story.title[:70]}...")
            logger.info(f"     Source: {story.source} | Status: {story.filter_status}{scraping_info}{summary_info}")
            if story.filter_reason:
                logger.info(f"     Reason: {story.filter_reason}")
            logger.info("")
        
    except Exception as e:
        logger.error(f"Error listing stories: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Flush specific stories from Redis storage',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python flush_story.py --list                     # List recent stories
  python flush_story.py --id story_123             # Delete specific story
  python flush_story.py --pattern "2025-06-20"    # Delete stories from specific date
  python flush_story.py --pattern "chelsea"       # Delete stories with 'chelsea' in ID
        """
    )
    
    parser.add_argument(
        '--id',
        help='Exact story ID to delete'
    )
    
    parser.add_argument(
        '--pattern',
        help='Delete stories whose IDs contain this pattern (case-insensitive)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List recent stories (useful for finding story IDs)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Number of stories to show when listing (default: 10)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate arguments
    if not (args.id or args.pattern or args.list):
        parser.error("Must specify --id, --pattern, or --list")
    
    if sum(bool(x) for x in [args.id, args.pattern, args.list]) > 1:
        parser.error("Can only specify one of --id, --pattern, or --list")
    
    try:
        # Load configuration
        config = load_config()
        storage_config = config.get("storage", {})
        redis_url = storage_config.get("redis_url", "redis://localhost:6379/0")
        
        logger.info(f"Connecting to Redis: {redis_url}")
        
        # Initialize storage
        storage = RedisStorage(redis_url)
        
        # Get total story count
        total_count = storage.get_story_count()
        logger.info(f"Total stories in database: {total_count}")
        
        if args.list:
            # List recent stories
            list_recent_stories(storage, args.limit)
            
        elif args.id:
            # Delete specific story
            logger.info(f"Attempting to delete story: {args.id}")
            success = flush_story_by_id(storage, args.id)
            if success:
                new_count = storage.get_story_count()
                logger.info(f"Story count: {total_count} -> {new_count}")
            
        elif args.pattern:
            # Delete stories by pattern
            logger.info(f"Searching for stories matching pattern: '{args.pattern}'")
            deleted_count = flush_stories_by_pattern(storage, args.pattern)
            if deleted_count > 0:
                new_count = storage.get_story_count()
                logger.info(f"Story count: {total_count} -> {new_count}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
