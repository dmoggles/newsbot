import logging
from typing import List, Dict, Any
from storage import Story

logger = logging.getLogger(__name__)

class StoryFilter:
    """Filters news stories based on source, headline, and URL criteria."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the filter with configuration settings."""
        filter_config = config.get("filter", {})
        
        # Source filtering
        self.confirmed_sources = set(filter_config.get("confirmed_sources", []))
        self.accepted_sources = set(filter_config.get("accepted_sources", []))
        
        # Keyword filtering
        self.banned_headline_keywords = [
            keyword.lower() for keyword in filter_config.get("banned_headline_keywords", [])
        ]
        self.banned_url_keywords = [
            keyword.lower() for keyword in filter_config.get("banned_url_keywords", [])
        ]
        
        logger.info(f"Initialized StoryFilter with {len(self.confirmed_sources)} confirmed sources, "
                   f"{len(self.accepted_sources)} accepted sources, "
                   f"{len(self.banned_headline_keywords)} banned headline keywords, "
                   f"{len(self.banned_url_keywords)} banned URL keywords")
        
        logger.debug(f"Confirmed sources: {self.confirmed_sources}")
        logger.debug(f"Accepted sources: {self.accepted_sources}")
        logger.debug(f"Banned headline keywords: {self.banned_headline_keywords}")
        logger.debug(f"Banned URL keywords: {self.banned_url_keywords}")
    
    def is_source_allowed(self, source: str) -> tuple[bool, str]:
        """
        Check if a source is allowed.
        
        Returns:
            tuple: (is_allowed, source_type) where source_type is 'confirmed', 'accepted', or 'banned'
        """
        if not source:
            logger.debug("Empty source provided")
            return False, "empty"
        
        source_lower = source.lower()
        
        # Check confirmed sources (exact match, case-insensitive)
        for confirmed_source in self.confirmed_sources:
            if confirmed_source.lower() in source_lower:
                logger.debug(f"Source '{source}' matches confirmed source '{confirmed_source}'")
                return True, "confirmed"
        
        # Check accepted sources (exact match, case-insensitive)
        for accepted_source in self.accepted_sources:
            if accepted_source.lower() in source_lower:
                logger.debug(f"Source '{source}' matches accepted source '{accepted_source}'")
                return True, "accepted"
        
        logger.debug(f"Source '{source}' not found in confirmed or accepted sources")
        return False, "banned"
    
    def has_banned_headline_keywords(self, headline: str) -> tuple[bool, List[str]]:
        """
        Check if headline contains banned keywords.
        
        Returns:
            tuple: (has_banned_keywords, list_of_found_keywords)
        """
        if not headline:
            return False, []
        
        headline_lower = headline.lower()
        found_keywords = []
        
        for banned_keyword in self.banned_headline_keywords:
            if banned_keyword in headline_lower:
                found_keywords.append(banned_keyword)
        
        if found_keywords:
            logger.debug(f"Headline '{headline}' contains banned keywords: {found_keywords}")
            return True, found_keywords
        
        return False, []
    
    def has_banned_url_keywords(self, url: str) -> tuple[bool, List[str]]:
        """
        Check if URL contains banned keywords.
        
        Returns:
            tuple: (has_banned_keywords, list_of_found_keywords)
        """
        if not url:
            return False, []
        
        url_lower = url.lower()
        found_keywords = []
        
        for banned_keyword in self.banned_url_keywords:
            if banned_keyword in url_lower:
                found_keywords.append(banned_keyword)
        
        if found_keywords:
            logger.debug(f"URL '{url}' contains banned keywords: {found_keywords}")
            return True, found_keywords
        
        return False, []
    
    def filter_story(self, story: Story) -> tuple[bool, str, Dict[str, Any]]:
        """
        Filter a single story based on all criteria.
        
        Returns:
            tuple: (should_keep, reason, metadata)
                - should_keep: True if story passes all filters
                - reason: Description of why story was kept/rejected
                - metadata: Additional information about the filtering decision
        """
        metadata = {
            "story_id": story.story_id,
            "source": story.source,
            "title": story.title[:100] + "..." if len(story.title) > 100 else story.title
        }
        
        # Check source filtering
        source_allowed, source_type = self.is_source_allowed(story.source)
        metadata["source_type"] = source_type
        
        if not source_allowed:
            reason = f"Source '{story.source}' not in confirmed or accepted sources"
            logger.info(f"FILTERED OUT: {reason} - {story.title}")
            return False, reason, metadata
        
        # Check headline keyword filtering
        has_banned_headline, banned_headline_keywords = self.has_banned_headline_keywords(story.title)
        if has_banned_headline:
            reason = f"Headline contains banned keywords: {banned_headline_keywords}"
            metadata["banned_headline_keywords"] = str(banned_headline_keywords)
            logger.info(f"FILTERED OUT: {reason} - {story.title}")
            return False, reason, metadata
        
        # Check URL keyword filtering
        has_banned_url, banned_url_keywords = self.has_banned_url_keywords(story.url)
        if has_banned_url:
            reason = f"URL contains banned keywords: {banned_url_keywords}"
            metadata["banned_url_keywords"] = str(banned_url_keywords)
            logger.info(f"FILTERED OUT: {reason} - {story.title}")
            return False, reason, metadata
        
        # Story passed all filters
        reason = f"Passed all filters (source: {source_type})"
        logger.debug(f"PASSED: {reason} - {story.title}")
        return True, reason, metadata
    
    def filter_stories(self, stories: List[Story]) -> tuple[List[Story], Dict[str, Any]]:
        """
        Filter a list of stories based on all criteria.
        
        Returns:
            tuple: (filtered_stories, filter_stats)
                - filtered_stories: List of stories that passed all filters
                - filter_stats: Statistics about the filtering process
        """
        if not stories:
            logger.info("No stories to filter")
            return [], {"total": 0, "passed": 0, "filtered_out": 0, "reasons": {}}
        
        logger.info(f"Starting to filter {len(stories)} stories")
        
        filtered_stories: List[Story] = []
        filter_stats: Dict[str, Any] = {
            "total": len(stories),
            "passed": 0,
            "filtered_out": 0,
            "reasons": {},
            "source_types": {"confirmed": 0, "accepted": 0}
        }
        
        for i, story in enumerate(stories, 1):
            try:
                should_keep, reason, metadata = self.filter_story(story)
                
                if should_keep:
                    filtered_stories.append(story)
                    filter_stats["passed"] += 1
                    
                    # Count source types for passed stories
                    source_type = metadata.get("source_type", "unknown")
                    if source_type in filter_stats["source_types"]:
                        filter_stats["source_types"][source_type] += 1
                else:
                    filter_stats["filtered_out"] += 1
                    
                    # Count reasons for filtering out
                    reason_key = reason.split(':')[0]  # Get the main reason category
                    if reason_key in filter_stats["reasons"]:
                        filter_stats["reasons"][reason_key] += 1
                    else:
                        filter_stats["reasons"][reason_key] = 1
                
                logger.debug(f"Processed story {i}/{len(stories)}: {story.title[:50]}...")
                
            except Exception as e:
                logger.error(f"Error filtering story {i}: {e}")
                logger.debug(f"Story data: {story}")
                filter_stats["filtered_out"] += 1
                if "error" in filter_stats["reasons"]:
                    filter_stats["reasons"]["error"] += 1
                else:
                    filter_stats["reasons"]["error"] = 1
                continue
        
        logger.info(f"Filtering complete: {filter_stats['passed']}/{filter_stats['total']} stories passed")
        logger.info(f"Source breakdown: {filter_stats['source_types']['confirmed']} confirmed, "
                   f"{filter_stats['source_types']['accepted']} accepted")
        
        if filter_stats["reasons"]:
            logger.info(f"Filter reasons: {filter_stats['reasons']}")
        
        return filtered_stories, filter_stats
