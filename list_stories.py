#!/usr/bin/env python3
"""
Script to display an ASCII table of all stories in the system with their filtering and scraping status.
"""

import sys
import os
from typing import List, Dict

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from storage import RedisStorage, Story, FilterStatus, ScrapingStatus


def format_status(status) -> str:
    """Format status for display, handling both enum and string values."""
    if status is None:
        return "None"
    return str(status).replace("FilterStatus.", "").replace("ScrapingStatus.", "")


def print_stories_table(stories: List[Story]) -> None:
    """Print an ASCII table of stories with their status."""
    if not stories:
        print("No stories found in the database.")
        return
    
    # Define column headers and widths
    headers = ["Story ID", "Filter Status", "Scraping Status", "Scraper Used", "Full Text", "Full Text Length"]
    col_widths = [15, 12, 14, 12, 10, 15]
    
    # Adjust column widths based on content
    for story in stories:
        col_widths[0] = max(col_widths[0], len(story.story_id))
        col_widths[1] = max(col_widths[1], len(format_status(story.filter_status)))
        col_widths[2] = max(col_widths[2], len(format_status(story.scraping_status)))
        col_widths[3] = max(col_widths[3], len(story.scraper_used or "None"))
        
    
    # Print table header
    header_line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    print(header_line)
    
    header_row = "|"
    for i, header in enumerate(headers):
        header_row += f" {header:<{col_widths[i]}} |"
    print(header_row)
    print(header_line)
    
    # Print table rows
    for story in stories:
        full_text_status = "Yes" if story.full_text and len(story.full_text.strip()) > 50 else "No"
        
        row = "|"
        row += f" {story.story_id:<{col_widths[0]}} |"
        row += f" {format_status(story.filter_status):<{col_widths[1]}} |"
        row += f" {format_status(story.scraping_status):<{col_widths[2]}} |"
        row += f" {(story.scraper_used or 'None'):<{col_widths[3]}} |"
        row += f" {full_text_status:<{col_widths[4]}} |"
        row += f" {len(story.full_text) if story.full_text else 0:<{col_widths[5]}} |"
        print(row)
    
    print(header_line)


def print_summary(stories: List[Story]) -> None:
    """Print a summary of story statistics."""
    total = len(stories)
    
    # Filter status summary
    filter_passed = sum(1 for s in stories if s.filter_status == FilterStatus.passed)
    filter_rejected = sum(1 for s in stories if s.filter_status == FilterStatus.rejected)
    filter_pending = sum(1 for s in stories if s.filter_status == FilterStatus.pending)
    filter_error = sum(1 for s in stories if s.filter_status == FilterStatus.error)
    filter_none = sum(1 for s in stories if s.filter_status is None)
    
    # Scraping status summary
    scraping_success = sum(1 for s in stories if s.scraping_status == ScrapingStatus.success)
    scraping_failed = sum(1 for s in stories if s.scraping_status == ScrapingStatus.failed)
    scraping_skipped = sum(1 for s in stories if s.scraping_status == ScrapingStatus.skipped)
    scraping_pending = sum(1 for s in stories if s.scraping_status == ScrapingStatus.pending)
    scraping_none = sum(1 for s in stories if s.scraping_status is None)
    
    # Scraper usage
    scrapers_used: Dict[str, int] = {}
    for story in stories:
        if story.scraper_used:
            scrapers_used[story.scraper_used] = scrapers_used.get(story.scraper_used, 0) + 1
    
    print("\n=== SUMMARY ===")
    print(f"Total stories: {total}")
    print("\nFilter Status:")
    print(f"  Passed:   {filter_passed}")
    print(f"  Rejected: {filter_rejected}")
    print(f"  Pending:  {filter_pending}")
    print(f"  Error:    {filter_error}")
    print(f"  None:     {filter_none}")
    
    print("\nScraping Status:")
    print(f"  Success:  {scraping_success}")
    print(f"  Failed:   {scraping_failed}")
    print(f"  Skipped:  {scraping_skipped}")
    print(f"  Pending:  {scraping_pending}")
    print(f"  None:     {scraping_none}")
    
    if scrapers_used:
        print("\nScrapers Used:")
        for scraper, count in sorted(scrapers_used.items()):
            print(f"  {scraper}: {count}")


def main():
    """Main function to display stories table."""
    try:
        # Initialize storage
        print("Connecting to Redis storage...")
        storage = RedisStorage()
        
        # Get all stories
        print("Fetching all stories...")
        stories = storage.get_all_stories()
        
        if not stories:
            print("No stories found in database.")
            return
        
        # Sort stories by story_id for consistent display
        stories.sort(key=lambda x: x.story_id)
        
        print(f"Found {len(stories)} stories in database.\n")
        
        # Print the table
        print_stories_table(stories)
        
        # Print summary
        print_summary(stories)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
