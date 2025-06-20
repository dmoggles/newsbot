#!/usr/bin/env python3
"""
Simple script to check how many stories are stored in Redis.
"""

import sys
sys.path.append('src')

from storage import RedisStorage
from config_loader import load_config

def check_redis_stories():
    """Check how many stories are in Redis."""
    
    try:
        # Load Redis URL from config
        config = load_config()
        storage_config = config.get("storage", {})
        redis_url = storage_config.get("redis_url", "redis://localhost:6379/0")
        
        print(f"Connecting to Redis at: {redis_url}")
        
        storage = RedisStorage(redis_url)
        
        # Get counts
        total_count = storage.get_story_count()
        
        print(f"Total stories in database: {total_count}")
        
        if total_count > 0:
            try:
                passed_count = len(storage.get_stories_by_filter_status("passed"))
                rejected_count = len(storage.get_stories_by_filter_status("rejected"))
                pending_count = len(storage.get_stories_by_filter_status("pending"))
                
                print(f"  - Passed: {passed_count}")
                print(f"  - Rejected: {rejected_count}")
                print(f"  - Pending: {pending_count}")
                print(f"  - Other: {total_count - passed_count - rejected_count - pending_count}")
                
            except Exception as e:
                print(f"Could not get detailed counts: {e}")
        
    except Exception as e:
        print(f"Error checking Redis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_redis_stories()
