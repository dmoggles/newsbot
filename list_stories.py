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


def calculate_summary_counted_length(story: Story) -> int:
    """
    Calculate the length of the summary that counts toward the 300-character limit.
    Per PRD: only summary text + byline + source name count, not the URL.
    """
    if not story.summary:
        return 0
    
    # Find the URL in markdown format [source](url) and exclude it from count
    summary = story.summary
    
    # Look for markdown link pattern at the end: [source](url)
    import re
    markdown_link_pattern = r'\[([^\]]+)\]\([^)]+\)$'
    match = re.search(markdown_link_pattern, summary)
    
    if match:
        # Extract the source name from the markdown link
        source_name = match.group(1)
        # Calculate counted length: everything except the URL part
        url_start = match.start()
        summary_without_url = summary[:url_start] + f"[{source_name}]"
        return len(summary_without_url)
    else:
        # No markdown link found, count the full summary
        return len(summary)


def print_stories_table(stories: List[Story]) -> None:
    """Print an ASCII table of stories with their status."""
    if not stories:
        print("No stories found in the database.")
        return
    
    # Define column headers and widths
    headers = ["Story ID", "Filter Status", "Scraping Status", "Scraper Used", "Full Text", "Full Text Length", "Has Summary", "Summary Length"]
    col_widths = [15, 12, 14, 12, 10, 15, 11, 14]
    
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
        has_summary = "Yes" if story.summary else "No"
        summary_length = calculate_summary_counted_length(story)
        
        row = "|"
        row += f" {story.story_id:<{col_widths[0]}} |"
        row += f" {format_status(story.filter_status):<{col_widths[1]}} |"
        row += f" {format_status(story.scraping_status):<{col_widths[2]}} |"
        row += f" {(story.scraper_used or 'None'):<{col_widths[3]}} |"
        row += f" {full_text_status:<{col_widths[4]}} |"
        row += f" {len(story.full_text) if story.full_text else 0:<{col_widths[5]}} |"
        row += f" {has_summary:<{col_widths[6]}} |"
        row += f" {summary_length:<{col_widths[7]}} |"
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
    
    # Summary statistics
    has_summary = sum(1 for s in stories if s.summary)
    no_summary = total - has_summary
    
    # Calculate average summary length (for stories that have summaries)
    summary_lengths = [calculate_summary_counted_length(s) for s in stories if s.summary]
    avg_summary_length = sum(summary_lengths) / len(summary_lengths) if summary_lengths else 0
    
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
    
    print("\nSummary Status:")
    print(f"  Has Summary:  {has_summary}")
    print(f"  No Summary:   {no_summary}")
    if summary_lengths:
        print(f"  Avg Length:   {avg_summary_length:.1f} chars (counted)")
        print(f"  Min Length:   {min(summary_lengths)} chars")
        print(f"  Max Length:   {max(summary_lengths)} chars")
    
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
