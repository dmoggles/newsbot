import logging
from typing import List, Dict, Any
from storage import Story, FilterStatus
from typechecking import as_str_key_dict

logger = logging.getLogger(__name__)


class StoryFilter:
    """Filters news stories based on source, headline, and URL criteria."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the filter with configuration settings."""
        filter_config = as_str_key_dict(config.get("filter", {}), str)

        # Source filtering
        self.confirmed_sources = set(filter_config.get("confirmed_sources", []))
        self.accepted_sources = set(filter_config.get("accepted_sources", []))

        # Keyword filtering
        self.banned_headline_keywords = [
            keyword.lower() for keyword in filter_config.get("banned_headline_keywords", [])
        ]
        self.banned_url_keywords = [keyword.lower() for keyword in filter_config.get("banned_url_keywords", [])]

        logger.info(
            "Initialized StoryFilter with %d confirmed sources, %d accepted sources, %d banned headline keywords, %d banned URL keywords",
            len(self.confirmed_sources),
            len(self.accepted_sources),
            len(self.banned_headline_keywords),
            len(self.banned_url_keywords),
        )

        logger.debug("Confirmed sources: %s", self.confirmed_sources)
        logger.debug("Accepted sources: %s", self.accepted_sources)
        logger.debug("Banned headline keywords: %s", self.banned_headline_keywords)
        logger.debug("Banned URL keywords: %s", self.banned_url_keywords)

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
                logger.debug("Source '%s' matches confirmed source '%s'", source, confirmed_source)
                return True, "confirmed"

        # Check accepted sources (exact match, case-insensitive)
        for accepted_source in self.accepted_sources:
            if accepted_source.lower() in source_lower:
                logger.debug("Source '%s' matches accepted source '%s'", source, accepted_source)
                return True, "accepted"

        logger.debug("Source '%s' not found in confirmed or accepted sources", source)
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
        found_keywords: List[str] = []

        for banned_keyword in self.banned_headline_keywords:
            if banned_keyword in headline_lower:
                found_keywords.append(banned_keyword)

        if found_keywords:
            logger.debug("Headline '%s' contains banned keywords: %s", headline, found_keywords)
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
        found_keywords: List[str] = []

        for banned_keyword in self.banned_url_keywords:
            if banned_keyword in url_lower:
                found_keywords.append(banned_keyword)

        if found_keywords:
            logger.debug("URL '%s' contains banned keywords: %s", url, found_keywords)
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
            "title": story.title[:100] + "..." if len(story.title) > 100 else story.title,
        }

        # Check source filtering
        source_allowed, source_type = self.is_source_allowed(story.source)
        metadata["source_type"] = source_type

        if not source_allowed:
            reason = "Source '%s' not in confirmed or accepted sources" % story.source
            logger.info("FILTERED OUT: %s - %s", reason, story.title)
            return False, reason, metadata  # Check headline keyword filtering
        has_banned_headline, banned_headline_keywords = self.has_banned_headline_keywords(story.title)
        if has_banned_headline:
            reason = "Headline contains banned keywords: %s" % banned_headline_keywords
            metadata["banned_headline_keywords"] = str(banned_headline_keywords)
            logger.info("FILTERED OUT: %s - %s", reason, story.title)
            return False, reason, metadata  # Check URL keyword filtering
        has_banned_url, banned_url_keywords = self.has_banned_url_keywords(story.url)
        if has_banned_url:
            reason = "URL contains banned keywords: %s" % banned_url_keywords
            metadata["banned_url_keywords"] = str(banned_url_keywords)
            logger.info("FILTERED OUT: %s - %s", reason, story.title)
            return False, reason, metadata  # Story passed all filters
        reason = "Passed all filters (source: %s)" % source_type
        logger.debug("PASSED: %s - %s", reason, story.title)
        return True, reason, metadata

    def filter_stories(self, stories: List[Story]) -> tuple[List[Story], Dict[str, Any]]:
        """
        Process a list of stories and update their filtering status in place.

        Returns:
            tuple: (all_stories_with_status, filter_stats)
                - all_stories_with_status: All stories with filter_status and filter_reason updated
                - filter_stats: Statistics about the filtering process
        """
        if not stories:
            logger.info("No stories to filter")
            return [], {"total": 0, "passed": 0, "filtered_out": 0, "reasons": {}}

        logger.info("Starting to process %d stories for filtering", len(stories))

        filter_stats: Dict[str, Any] = {
            "total": len(stories),
            "passed": 0,
            "filtered_out": 0,
            "reasons": {},
            "source_types": {"confirmed": 0, "accepted": 0},
        }

        for i, story in enumerate(stories, 1):
            try:
                should_keep, reason, metadata = self.filter_story(story)

                if should_keep:
                    # Story passed all filters
                    story.filter_status = FilterStatus.passed
                    story.filter_reason = reason
                    filter_stats["passed"] += 1

                    # Count source types for passed stories
                    source_type = metadata.get("source_type", "unknown")
                    if source_type in filter_stats["source_types"]:
                        filter_stats["source_types"][source_type] += 1
                else:
                    # Story was filtered out
                    story.filter_status = FilterStatus.rejected
                    story.filter_reason = reason
                    filter_stats["filtered_out"] += 1

                    # Count reasons for filtering out
                    reason_key = reason.split(":", maxsplit=1)[0]  # Get the main reason category
                    if reason_key in filter_stats["reasons"]:
                        filter_stats["reasons"][reason_key] += 1
                    else:
                        filter_stats["reasons"][reason_key] = 1

                logger.debug(
                    "Processed story %d/%d: %s... [%s]", i, len(stories), story.title[:50], story.filter_status
                )

            except Exception as e:
                logger.error("Error filtering story %d: %s", i, e)
                logger.debug("Story data: %s", story)
                story.filter_status = FilterStatus.error
                story.filter_reason = "Processing error: %s" % str(e)
                filter_stats["filtered_out"] += 1
                if "error" in filter_stats["reasons"]:
                    filter_stats["reasons"]["error"] += 1
                else:
                    filter_stats["reasons"]["error"] = 1
                continue

        logger.info("Filtering complete: %d/%d stories passed", filter_stats["passed"], filter_stats["total"])
        logger.info(
            "Source breakdown: %d confirmed, %d accepted",
            filter_stats["source_types"]["confirmed"],
            filter_stats["source_types"]["accepted"],
        )

        if filter_stats["reasons"]:
            logger.info("Filter reasons: %s", filter_stats["reasons"])

        return stories, filter_stats
