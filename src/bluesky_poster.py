"""BlueSky social media poster with rate limiting and post tracking."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List
from blueskysocial import Client, Post, WebCard
from storage import Story, PostStatus


class BlueSkyPoster:
    """Handles posting stories to BlueSky with rate limiting and tracking."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the BlueSky poster with configuration.

        Args:
            config: Configuration dictionary containing BlueSky credentials and settings
        """
        self.logger = logging.getLogger(__name__)

        # Extract BlueSky configuration
        bluesky_config = config.get("bluesky", {})
        self.handle = bluesky_config.get("handle", "")
        self.app_password = bluesky_config.get("app_password", "")

        # Extract rate limiting configuration
        rate_limit_config = config.get("rate_limit", {})
        self.post_interval_minutes = rate_limit_config.get("post_interval_minutes", 30)

        # Initialize BlueSky client
        if self.handle and self.app_password:
            try:
                self.client = Client()
                self.authenticated = False
                self.logger.info("BlueSky client initialized")
            except Exception as e:
                self.logger.error("Failed to initialize BlueSky client: %s", e)
                self.client = None
                self.authenticated = False
        else:
            self.client = None
            self.authenticated = False
            self.logger.warning("BlueSky credentials not configured")

        self.last_successful_post_time: Optional[datetime] = None

        self.logger.info(
            "Initialized BlueSkyPoster with handle: %s, post_interval: %d minutes",
            self.handle,
            self.post_interval_minutes,
        )

    def authenticate(self) -> bool:
        """
        Authenticate with BlueSky using configured credentials.

        Returns:
            bool: True if authentication successful, False otherwise
        """
        if not self.handle or not self.app_password:
            self.logger.error("BlueSky handle or app_password not configured")
            return False

        try:
            self.client = Client()
            self.client.authenticate(self.handle, self.app_password)
            self.authenticated = True
            self.logger.info("Successfully authenticated with BlueSky")
            return True

        except Exception as e:
            self.logger.error("Failed to authenticate with BlueSky: %s", e)
            self.authenticated = False
            return False

    def can_post_now(self) -> Tuple[bool, str]:
        """
        Check if a new post can be made based on rate limiting rules.

        Returns:
            Tuple[bool, str]: (can_post, reason)
        """
        if self.last_successful_post_time is None:
            return True, "No previous posts"

        time_since_last_post = datetime.now() - self.last_successful_post_time
        required_interval = timedelta(minutes=self.post_interval_minutes)

        if time_since_last_post >= required_interval:
            return True, f"Sufficient time elapsed: {time_since_last_post}"

        remaining = required_interval - time_since_last_post
        return False, f"Rate limit active, {remaining} remaining"

    def post_story(self, story: Story) -> Tuple[PostStatus, str]:
        """
        Post a single story to BlueSky.

        Args:
            story: Story object to post

        Returns:
            Tuple[PostStatus, str]: (status, reason)
        """
        # Check authentication
        if not self.authenticated:
            if not self.authenticate():
                return PostStatus.failed, "Authentication failed"

        # Check rate limiting
        can_post, rate_limit_reason = self.can_post_now()
        if not can_post:
            return PostStatus.skipped, f"Rate limited: {rate_limit_reason}"

        # Prepare post content
        if not story.summary:
            return PostStatus.failed, "No summary available for posting"

        post_text = story.summary

        try:
            # Create Post object and post to BlueSky
            url = story.url or story.decoded_url
            if not url:
                post_obj = Post(post_text)
            else:
                try:
                    webcard = WebCard(url)
                    post_obj = Post(post_text, with_attachments=webcard)
                except Exception as e:
                    self.logger.error("Failed to create web card for URL %s: %s", url, e)
                    post_obj = Post(post_text)
            assert self.client is not None, "BlueSky client is not initialized"
            self.client.post(post_obj)

            # Update rate limiting tracker            self.last_successful_post_time = datetime.now()

            self.logger.info("Successfully posted story %s to BlueSky", story.story_id)
            return PostStatus.posted, f"Posted successfully at {self.last_successful_post_time}"

        except Exception as e:
            self.logger.error("Failed to post story %s to BlueSky: %s", story.story_id, e)
            return PostStatus.failed, f"Post failed: {str(e)}"

    def post_stories(self, stories: list[Story]) -> Dict[str, Any]:
        """
        Post multiple stories to BlueSky, respecting rate limits.

        Args:
            stories: List of Story objects to post

        Returns:
            Dict[str, Any]: Statistics about posting results
        """
        stats = {"total": len(stories), "posted": 0, "failed": 0, "skipped": 0, "rate_limited": 0}

        posted_stories: List[Story] = []

        for story in stories:
            # Skip stories that already have a post status of posted
            if story.post_status == PostStatus.posted:
                stats["skipped"] += 1
                self.logger.info("Skipping story %s - already posted", story.story_id)
                continue

            # Skip stories that don't have summaries or are not relevant
            if not story.summary:
                story.post_status = PostStatus.failed
                story.post_reason = "No summary available"
                stats["failed"] += 1
                continue

            # Skip stories that are not relevant (if relevance check was performed)
            if hasattr(story, "relevance_status") and story.relevance_status == "not_relevant":
                story.post_status = PostStatus.skipped
                story.post_reason = "Story not relevant"
                stats["skipped"] += 1
                continue

            # Attempt to post
            post_status, post_reason = self.post_story(story)
            story.post_status = post_status
            story.post_reason = post_reason

            # Set posted_at timestamp if successfully posted
            if post_status == PostStatus.posted:
                story.posted_at = self.last_successful_post_time.isoformat() if self.last_successful_post_time else None

            if post_status == PostStatus.posted:
                stats["posted"] += 1
                posted_stories.append(story)
                # Only post one story per run due to rate limiting
                break
            elif post_status == PostStatus.failed:
                stats["failed"] += 1
            elif post_status == PostStatus.skipped:
                if "Rate limited" in post_reason:
                    stats["rate_limited"] += 1
                else:
                    stats["skipped"] += 1

        self.logger.info("Posting complete: %s", stats)
        return stats

    def set_last_post_time(self, last_post_time: datetime):
        """
        Set the last successful post time (useful for initialization from storage).

        Args:
            last_post_time: DateTime of the last successful post"""
        self.last_successful_post_time = last_post_time
        self.logger.info("Set last successful post time to: %s", last_post_time)
