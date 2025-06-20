from enum import Enum
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
import redis
import json

class PostStatus(str, Enum):
    posted = "posted"
    failed = "failed"
    skipped = "skipped"
    pending = "pending"

class FilterStatus(str, Enum):
    passed = "passed"
    rejected = "rejected"
    pending = "pending"
    error = "error"

class ScrapingStatus(str, Enum):
    success = "success"
    failed = "failed"
    skipped = "skipped"
    pending = "pending"

class RelevanceStatus(str, Enum):
    relevant = "relevant"
    not_relevant = "not_relevant"
    pending = "pending"
    skipped = "skipped"  # For confirmed sources

class Story(BaseModel):
    story_id: str
    title: str
    url: str
    date: str
    source: str
    byline: Optional[str] = None
    decoded_url: Optional[str] = None
    google_redirect_url: Optional[str] = None  # Store original Google News redirect URL
    description: Optional[str] = None  # RSS description/summary
    full_text: Optional[str] = None
    summary: Optional[str] = None
    post_status: Optional[PostStatus] = None
    filter_status: Optional[FilterStatus] = None
    filter_reason: Optional[str] = None
    scraping_status: Optional[ScrapingStatus] = None
    scraping_error: Optional[Dict[str, str]] = None  # Dict of scraper_name -> error_message
    scraper_used: Optional[str] = None  # Which scraper was used (newspaper3k, trafilatura, etc.)
    relevance_status: Optional[RelevanceStatus] = None
    relevance_reason: Optional[str] = None
    post_reason: Optional[str] = None  # Reason for post status (success message, error, etc.)
    posted_at: Optional[str] = None  # ISO timestamp when successfully posted
    # Add more fields as needed

class RedisStorage:
    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.client: redis.Redis = redis.Redis.from_url(url)

    def save_story(self, story: Story) -> None:
        # Serialize each field as JSON for consistency
        data = {k: json.dumps(v) for k, v in story.model_dump().items()}
        # Ensure all values are str, as required by redis-py type hints
        data_str = {k: str(v) for k, v in data.items()}
        self.client.hset(f"story:{story.story_id}", mapping=data_str)

    def get_story(self, story_id: str) -> Optional[Story]:
        result = self.client.hgetall(f"story:{story_id}")
        if not result:
            return None
        data: Dict[str, Any] = {k.decode(): json.loads(v) for k, v in result.items()}
        return Story(**data)

    def story_exists(self, story_id: str) -> bool:
        return self.client.exists(f"story:{story_id}") == 1

    def update_story(self, story: Story) -> None:
        self.save_story(story)

    def get_all_stories(self) -> List[Story]:
        keys: List[bytes] = self.client.keys("story:*")
        stories: List[Story] = []
        for key in keys:
            story_id = key.decode().split(":", 1)[1]
            story = self.get_story(story_id)
            if story:
                stories.append(story)
        return stories

    def get_story_count(self) -> int:
        """Get the total number of stories in storage."""
        return len(self.client.keys("story:*"))
    
    def get_stories_by_filter_status(self, filter_status: str) -> List[Story]:
        """Get all stories with a specific filter status."""
        all_stories = self.get_all_stories()
        return [story for story in all_stories if story.filter_status == filter_status]
    
    def delete_story(self, story_id: str) -> bool:
        """
        Delete a story from storage.
        
        Args:
            story_id: ID of the story to delete
            
        Returns:
            True if story was deleted, False if it didn't exist
        """
        key = f"story:{story_id}"
        result = self.client.delete(key)
        return result > 0
    
    def get_last_successful_post_time(self) -> Optional[str]:
        """
        Get the timestamp of the most recent successful post.
        
        Returns:
            ISO timestamp string of the last successful post, or None if no posts found
        """
        all_stories = self.get_all_stories()
        posted_stories = [
            story for story in all_stories 
            if story.post_status == PostStatus.posted and story.posted_at
        ]
        
        if not posted_stories:
            return None
        
        # Sort by posted_at timestamp and return the most recent
        posted_stories.sort(key=lambda s: s.posted_at or "", reverse=True)
        return posted_stories[0].posted_at
    
    def get_postable_stories(self) -> List[Story]:
        """
        Get stories that are ready to be posted (have summaries, passed relevance checks, not yet posted).
        
        Returns:
            List of stories that can be posted
        """
        all_stories = self.get_all_stories()
        postable = []
        
        for story in all_stories:
            # Must have a summary
            if not story.summary:
                continue
            
            # Must not already be posted
            if story.post_status == PostStatus.posted:
                continue
            
            # Must have passed filtering
            if story.filter_status != FilterStatus.passed:
                continue
            
            # If relevance check was performed, must be relevant
            if (hasattr(story, 'relevance_status') and 
                story.relevance_status and 
                story.relevance_status != RelevanceStatus.relevant):
                continue
            
            postable.append(story)
        
        return postable
