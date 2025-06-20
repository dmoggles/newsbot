#!/usr/bin/env python3
"""
Script to flush all stored stories from Redis.
This is useful for testing and resetting the database.
"""

import sys
import argparse
sys.path.append('src')

from storage import RedisStorage
from config_loader import load_config

def flush_stories(redis_url: str, confirm: bool = False) -> None:
    """Flush all stories from Redis storage."""
    
    print(f"Connecting to Redis at: {redis_url}")
    
    try:
        storage = RedisStorage(redis_url)
        
        # Get current count
        current_count = storage.get_story_count()
        print(f"Current stories in database: {current_count}")
        
        if current_count == 0:
            print("No stories to flush.")
            return
        
        # Confirm deletion
        if not confirm:
            response = input(f"Are you sure you want to delete all {current_count} stories? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Operation cancelled.")
                return
        
        # Get all story keys
        client = storage.client
        story_keys = client.keys("story:*")
        
        if story_keys:
            print(f"Deleting {len(story_keys)} story records...")
            deleted_count = client.delete(*story_keys)
            print(f"Successfully deleted {deleted_count} story records.")
        else:
            print("No story records found to delete.")
        
        # Verify deletion
        final_count = storage.get_story_count()
        print(f"Stories remaining: {final_count}")
        
        if final_count == 0:
            print("✅ All stories successfully flushed from Redis.")
        else:
            print(f"⚠️  Warning: {final_count} stories still remain in database.")
            
    except Exception as e:
        print(f"❌ Error flushing stories: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Flush all stored stories from Redis')
    parser.add_argument(
        '--redis-url',
        type=str,
        help='Redis URL (default: from config or redis://localhost:6379/0)'
    )
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Confirm deletion without prompting'
    )
    parser.add_argument(
        '--config',
        action='store_true',
        help='Load Redis URL from config file'
    )
    
    args = parser.parse_args()
    
    # Determine Redis URL
    redis_url = None
    
    if args.redis_url:
        redis_url = args.redis_url
    elif args.config:
        try:
            config = load_config()
            storage_config = config.get("storage", {})
            redis_url = storage_config.get("redis_url", "redis://localhost:6379/0")
            print(f"Loaded Redis URL from config: {redis_url}")
        except Exception as e:
            print(f"Failed to load config: {e}")
            sys.exit(1)
    else:
        redis_url = "redis://localhost:6379/0"
    
    print("=" * 60)
    print("REDIS STORY FLUSH UTILITY")
    print("=" * 60)
    print(f"Target Redis: {redis_url}")
    print()
    
    flush_stories(redis_url, args.yes)

if __name__ == "__main__":
    main()
