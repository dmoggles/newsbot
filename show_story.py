#!/usr/bin/env python3
"""
Script to display the full content of a specific story by ID.
"""

import sys
import os
import json
from typing import Optional

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from storage import RedisStorage, Story


def print_story_details(story: Story) -> None:
    """Print detailed information about a story."""
    print("=" * 80)
    print(f"STORY DETAILS: {story.story_id}")
    print("=" * 80)
    
    # Basic information
    print(f"Title:       {story.title}")
    print(f"URL:         {story.url}")
    print(f"Date:        {story.date}")
    print(f"Source:      {story.source}")
    print(f"Byline:      {story.byline or 'None'}")
    print(f"Description: {story.description or 'None'}")
    
    # URLs
    print("\nURL Information:")
    print(f"  Original URL:     {story.url}")
    print(f"  Decoded URL:      {story.decoded_url or 'None'}")
    print(f"  Google Redirect:  {story.google_redirect_url or 'None'}")
    
    # Status information
    print("\nStatus Information:")
    print(f"  Post Status:      {story.post_status or 'None'}")
    print(f"  Filter Status:    {story.filter_status or 'None'}")
    print(f"  Filter Reason:    {story.filter_reason or 'None'}")
    print(f"  Scraping Status:  {story.scraping_status or 'None'}")
    print(f"  Scraper Used:     {story.scraper_used or 'None'}")
    
    # Scraping errors (if any)
    if story.scraping_error:
        print("\nScraping Errors:")
        if isinstance(story.scraping_error, dict):
            for scraper, error in story.scraping_error.items():
                print(f"  {scraper}: {error}")
        else:
            print(f"  {story.scraping_error}")
    
    # Content
    print("\nContent:")
    print(f"  Summary Length:   {len(story.summary) if story.summary else 0} characters")
    print(f"  Full Text Length: {len(story.full_text) if story.full_text else 0} characters")
    
    if story.summary:
        print("\nSummary:")
        print("-" * 40)
        print(story.summary)
    
    if story.full_text:
        print("\nFull Text:")
        print("-" * 40)
        print(story.full_text)
    
    # Raw data (for debugging)
    print("\nRaw Story Data (JSON):")
    print("-" * 40)
    story_dict = story.model_dump()
    # Truncate full_text for readability in JSON output
    if story_dict.get('full_text') and len(story_dict['full_text']) > 200:
        story_dict['full_text'] = story_dict['full_text'][:200] + "... [truncated]"
    print(json.dumps(story_dict, indent=2, default=str))
    
    print("=" * 80)


def find_story_by_partial_id(storage: RedisStorage, partial_id: str) -> Optional[Story]:
    """Find a story by partial ID match."""
    all_stories = storage.get_all_stories()
    matches = [story for story in all_stories if partial_id.lower() in story.story_id.lower()]
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"Multiple stories match '{partial_id}':")
        for story in matches:
            print(f"  {story.story_id}")
        print("Please be more specific.")
        return None
    else:
        return None


def main():
    """Main function to display story details."""
    if len(sys.argv) != 2:
        print("Usage: python show_story.py <story_id>")
        print("You can use a partial story ID - if unique, it will be matched.")
        print("\nTo see all available story IDs, run: python list_stories.py")
        sys.exit(1)
    
    story_id = sys.argv[1]
    
    try:
        # Initialize storage
        print("Connecting to Redis storage...")
        storage = RedisStorage()
        
        # Try to get story by exact ID first
        story = storage.get_story(story_id)
        
        # If not found, try partial match
        if not story:
            print(f"Story '{story_id}' not found. Trying partial match...")
            story = find_story_by_partial_id(storage, story_id)
        
        if not story:
            print(f"No story found matching '{story_id}'")
            print("To see all available story IDs, run: python list_stories.py")
            sys.exit(1)
        
        # Print story details
        print_story_details(story)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
