
from enum import Enum
import json
from typing import Any, Dict, Optional, List, cast
from pydantic import BaseModel
import redis
from typechecking import as_int

class PostStatus(str, Enum):
    """
    Enumeration representing the status of a post.

    Attributes:
        posted: Indicates the post has been successfully published.
        failed: Indicates the post failed to be published.
        skipped: Indicates the post was intentionally skipped and not published.
        pending: Indicates the post is awaiting publication.
    """
    posted = "posted"
    failed = "failed"
    skipped = "skipped"
    pending = "pending"

class FilterStatus(str, Enum):
    """
    Enumeration representing the status of a filter operation.

    Attributes:
        passed: Indicates the filter operation was successful.
        rejected: Indicates the filter operation was unsuccessful or denied.
        pending: Indicates the filter operation is still in progress or awaiting a result.
        error: Indicates an error occurred during the filter operation.
    """
    passed = "passed"
    rejected = "rejected"
    pending = "pending"
    error = "error"

class ScrapingStatus(str, Enum):
    """
    Enumeration representing the possible statuses of a scraping operation.

    Attributes:
        success: Indicates that the scraping operation completed successfully.
        failed: Indicates that the scraping operation failed.
        skipped: Indicates that the scraping operation was skipped.
        pending: Indicates that the scraping operation is pending and has not yet completed.
    """
    success = "success"
    failed = "failed"
    skipped = "skipped"
    pending = "pending"

class RelevanceStatus(str, Enum):
    """
    Enumeration representing the relevance status of a news item or source.

    Attributes:
        relevant (str): Indicates the item is relevant.
        not_relevant (str): Indicates the item is not relevant.
        pending (str): Indicates the relevance of the item is pending review.
        skipped (str): Indicates the item was skipped, typically for confirmed sources.
    """
    relevant = "relevant"
    not_relevant = "not_relevant"
    pending = "pending"
    skipped = "skipped"  # For confirmed sources

class Story(BaseModel):
    """
    Represents a news story with metadata, content, and processing statuses.

    Attributes:
        story_id (str): Unique identifier for the story.
        title (str): Title of the story.
        url (str): Original URL of the story.
        date (str): Publication date of the story.
        source (str): Source or publisher of the story.
        byline (Optional[str]): Author or byline information.
        decoded_url (Optional[str]): Decoded version of the story URL.
        google_redirect_url (Optional[str]): Original Google News redirect URL.
        description (Optional[str]): RSS description or summary of the story.
        full_text (Optional[str]): Full text content of the story.
        summary (Optional[str]): Generated or provided summary of the story.
        post_status (Optional[PostStatus]): Status of posting the story.
        filter_status (Optional[FilterStatus]): Status of filtering the story.
        filter_reason (Optional[str]): Reason for the filter status.
        scraping_status (Optional[ScrapingStatus]): Status of scraping the story.
        scraping_error (Optional[Dict[str, str]]): Mapping of scraper name to error message.
        scraper_used (Optional[str]): Name of the scraper used (e.g., newspaper3k, trafilatura).
        relevance_status (Optional[RelevanceStatus]): Status indicating story relevance.
        relevance_reason (Optional[str]): Reason for the relevance status.
        post_reason (Optional[str]): Reason for the post status (success message, error, etc.).
        posted_at (Optional[str]): ISO timestamp when the story was successfully posted.
    """
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
    """
    RedisStorage provides an interface for storing, retrieving, updating, and deleting Story objects in a Redis database.
    Attributes:
        client (redis.Redis): The Redis client instance used for database operations.
        url (str): The Redis connection URL. Defaults to "redis://localhost:6379/0".
    Methods:
        save_story(story: Story) -> None:
            Save a Story object to Redis, serializing its fields as JSON.
        get_story(story_id: str) -> Optional[Story]:
            Retrieve a Story object from Redis by its ID.
        story_exists(story_id: str) -> bool:
            Check if a story with the given ID exists in Redis.
        update_story(story: Story) -> None:
            Update an existing Story object in Redis.
        get_all_stories() -> List[Story]:
            Retrieve all Story objects stored in Redis.
        get_story_count() -> int:
            Get the total number of stories in storage.
        get_stories_by_filter_status(filter_status: str) -> List[Story]:
            Get all stories with a specific filter status.
        delete_story(story_id: str) -> bool:
            Delete a story from storage by its ID.
        get_last_successful_post_time() -> Optional[str]:
        get_postable_stories() -> List[Story]:
    """

    def __init__(self, url: str = "redis://localhost:6379/0"):
        self.client = redis.Redis.from_url(url) #type: ignore

    def save_story(self, story: Story) -> None:
        """
        Saves a Story object to Redis as a hash.

        Each field of the Story is serialized to JSON for consistency, then stored as a string
        in a Redis hash with a key formatted as "story:{story_id}".

        Args:
            story (Story): The Story object to be saved.

        Returns:
            None
        """
        # Serialize each field as JSON for consistency
        data =  {str(k): json.dumps(v) for k, v in story.model_dump().items()}
        self.client.hset(f"story:{story.story_id}", mapping=data) #type: ignore

    def get_story(self, story_id: str) -> Optional[Story]:
        """
        Retrieve a story from the storage by its ID.

        Args:
            story_id (str): The unique identifier of the story to retrieve.

        Returns:
            Optional[Story]: The Story object if found, otherwise None.
        """
        result = cast(Dict[bytes, bytes], self.client.hgetall(f"story:{story_id}")) #type: ignore
        if not result:
            return None
        data: Dict[str, Any] = {k.decode(): json.loads(v) for k, v in result.items()}
        return Story(**data)

    def story_exists(self, story_id: str) -> bool:
        """
        Check if a story with the given story_id exists in the storage.

        Args:
            story_id (str): The unique identifier of the story to check.

        Returns:
            bool: True if the story exists, False otherwise.
        """
        return self.client.exists(f"story:{story_id}") == 1

    def update_story(self, story: Story) -> None:
        """
        Updates an existing story in the storage.

        This method saves the provided Story object, overwriting any existing entry
        with the same identifier.

        Args:
            story (Story): The Story object to be updated in the storage.

        Returns:
            None
        """
        self.save_story(story)

    def get_all_stories(self) -> List[Story]:
        """
        Retrieves all stories stored in the database.

        Returns:
            List[Story]: A list of all Story objects found in the storage.
        """
        keys: List[bytes] = self.client.keys("story:*") #type: ignore
        stories: List[Story] = []
        for key in keys:
            story_id = key.decode().split(":", 1)[1]
            story = self.get_story(story_id)
            if story:
                stories.append(story)
        return stories

    def get_story_count(self) -> int:
        """
        Returns the total number of stories stored.

        This method queries the storage backend for all keys matching the pattern "story:*"
        and returns the count of such keys.

        Returns:
            int: The total number of stories currently stored.
        """
        
        return len(self.client.keys("story:*")) #type: ignore
    
    def get_stories_by_filter_status(self, filter_status: str) -> List[Story]:
        """
        Retrieve all stories that have the specified filter status.

        Args:
            filter_status (str): The filter status to match against each story.

        Returns:
            List[Story]: A list of stories whose filter_status matches the provided value.
        """
        
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
        result = as_int(self.client.delete(key))
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
        postable: List[Story] = []
        
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
