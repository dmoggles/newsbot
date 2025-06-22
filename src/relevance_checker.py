"""
Relevance checker for verifying story relevance to specified topics.

This module implements relevance checking for accepted sources (non-confirmed sources).
Confirmed sources automatically pass relevance checks.
"""

import logging
from typing import Dict, Any, List, Tuple
from storage import Story, RelevanceStatus

logger = logging.getLogger(__name__)


class RelevanceChecker:
    """Checks story relevance using configurable strategies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the relevance checker with configuration settings."""
        relevance_config = config.get("relevance_checker", {})
        
        # Get relevance keywords
        self.keywords = [
            keyword.lower() for keyword in relevance_config.get("keywords", [])
        ]
        
        # Get strategy (currently only 'substring' is supported)
        self.strategy = relevance_config.get("strategy", "substring")
        
        if not self.keywords:
            logger.warning("No relevance keywords configured - all stories will be considered relevant")
        
        logger.info("Initialized RelevanceChecker with strategy '%s' and keywords: %s", self.strategy, self.keywords)
        
    def is_relevant(self, story: Story, source_type: str) -> Tuple[bool, str]:
        """
        Check if a story is relevant to our configured topics.
        
        Args:
            story: The story to check
            source_type: Type of source ('confirmed' or 'accepted')
            
        Returns:
            Tuple of (is_relevant, reason)
        """
        # Confirmed sources automatically pass relevance checks
        if source_type == "confirmed":
            logger.debug("Story %s from confirmed source - skipping relevance check", story.story_id)
            return True, "Confirmed source - relevance check skipped"
        
        # If no keywords configured, consider everything relevant
        if not self.keywords:
            logger.debug("No relevance keywords configured - story %s considered relevant", story.story_id)
            return True, "No relevance keywords configured"
        
        # Check relevance based on strategy
        if self.strategy == "substring":
            return self._check_substring_relevance(story)
        else:
            logger.warning("Unknown relevance strategy '%s' - falling back to substring", self.strategy)
            return self._check_substring_relevance(story)
    
    def _check_substring_relevance(self, story: Story) -> Tuple[bool, str]:
        """
        Check relevance using substring matching strategy.
        
        Args:
            story: The story to check
            
        Returns:
            Tuple of (is_relevant, reason)
        """
        # Check summary first (preferred), then title as fallback
        text_to_check = story.summary or story.title or ""
        
        if not text_to_check:
            logger.warning("Story %s has no summary or title to check relevance", story.story_id)
            return False, "No text available for relevance checking"
        
        text_lower = text_to_check.lower()
        matched_keywords: List[str] = []
        
        # Check each keyword
        for keyword in self.keywords:
            if keyword in text_lower:
                matched_keywords.append(keyword)
        
        if matched_keywords:
            reason = f"Matched relevance keywords: {', '.join(matched_keywords)}"
            logger.debug("Story %s is relevant - %s", story.story_id, reason)
            return True, reason
        else:
            reason = f"No relevance keywords found in text. Checked: {', '.join(self.keywords)}"
            logger.debug("Story %s is not relevant - %s", story.story_id, reason)
            return False, reason
    
    def check_stories(self, stories: List[Story], source_types: Dict[str, str]) -> Tuple[List[Story], Dict[str, Any]]:
        """
        Check relevance for multiple stories.
        
        Args:
            stories: List of stories to check
            source_types: Dict mapping story_id to source_type
            
        Returns:
            Tuple of (processed_stories, stats)
        """
        processed_stories: List[Story] = []
        stats: Dict[str, Any] = {
            "total": len(stories),
            "relevant": 0,
            "not_relevant": 0,
            "confirmed_skipped": 0,
            "keywords_matched": {}
        }
        
        for story in stories:
            source_type = source_types.get(story.story_id, "accepted")
            is_relevant, reason = self.is_relevant(story, source_type)
            
            # Update story with relevance information
            story.relevance_status = RelevanceStatus.relevant if is_relevant else RelevanceStatus.not_relevant
            story.relevance_reason = reason
            
            processed_stories.append(story)
            
            # Update stats
            if source_type == "confirmed":
                stats["confirmed_skipped"] += 1
            elif is_relevant:
                stats["relevant"] += 1
                # Track which keywords were matched
                if "Matched relevance keywords:" in reason:
                    keywords = reason.split(": ", 1)[1].split(", ")
                    for keyword in keywords:
                        stats["keywords_matched"][keyword] = stats["keywords_matched"].get(keyword, 0) + 1
            else:
                stats["not_relevant"] += 1
        
        logger.info(
            "Relevance check completed: %d total, %d relevant, %d not relevant, %d confirmed sources skipped",
            stats['total'], stats['relevant'], stats['not_relevant'], stats['confirmed_skipped']
        )
        
        return processed_stories, stats
