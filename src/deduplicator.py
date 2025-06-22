import logging
import hashlib
from typing import List, Dict, Set, Tuple
from urllib.parse import urlparse, parse_qs
from storage import Story

logger = logging.getLogger(__name__)


class StoryDeduplicator:
    """Handles deduplication of news stories using URL and headline hashes."""

    def __init__(self) -> None:
        self.url_hashes: Set[str] = set()
        self.headline_hashes: Set[str] = set()
        self.existing_story_ids: Set[str] = set()

    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication by removing tracking parameters and fragments.
        """
        try:
            parsed = urlparse(url)

            # Remove common tracking parameters
            tracking_params = {
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_term",
                "utm_content",
                "fbclid",
                "gclid",
                "msclkid",
                "ref",
                "source",
                "campaign_id",
                "_ga",
                "_gac",
                "_gid",
                "mc_cid",
                "mc_eid",
            }

            if parsed.query:
                params = parse_qs(parsed.query)
                filtered_params = {k: v for k, v in params.items() if k not in tracking_params}
                query_string = "&".join(f"{k}={v[0]}" for k, v in filtered_params.items())
            else:
                query_string = ""
            # Reconstruct URL without fragment and with filtered parameters
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if query_string:
                normalized += f"?{query_string}"

            return normalized.lower()

        except Exception as e:
            logger.warning("Failed to normalize URL %s: %s", url, e)
            return url.lower()

    def _normalize_headline(self, headline: str) -> str:
        """
        Normalize headline for deduplication by removing common variations.
        """
        # Remove extra whitespace and convert to lowercase
        normalized = " ".join(headline.lower().split())

        # Remove common punctuation that might vary
        punctuation_to_remove = ['"', "'", '"', '"', """, """]
        for punct in punctuation_to_remove:
            normalized = normalized.replace(punct, "")

        # Remove trailing punctuation that might vary
        normalized = normalized.rstrip(".,!?;:")

        return normalized

    def _get_url_hash(self, url: str) -> str:
        """Generate hash for normalized URL."""
        normalized_url = self._normalize_url(url)
        return hashlib.md5(normalized_url.encode("utf-8")).hexdigest()

    def _get_headline_hash(self, headline: str) -> str:
        """Generate hash for normalized headline."""
        normalized_headline = self._normalize_headline(headline)
        return hashlib.md5(normalized_headline.encode("utf-8")).hexdigest()

    def _is_google_news_redirect(self, url: str) -> bool:
        """Check if URL is a Google News redirect URL."""
        return "news.google.com" in url and "/articles/" in url

    def load_existing_stories(self, existing_stories: List[Story]) -> None:
        """
        Load existing stories to build deduplication index.
        """
        logger.info("Loading %d existing stories for deduplication", len(existing_stories))

        self.url_hashes.clear()
        self.headline_hashes.clear()
        self.existing_story_ids.clear()

        for story in existing_stories:
            # Add story ID
            self.existing_story_ids.add(story.story_id)

            # Add URL hash (skip Google News redirects as they're not reliable)
            if not self._is_google_news_redirect(story.url):
                url_hash = self._get_url_hash(story.url)
                self.url_hashes.add(url_hash)
            # Add headline hash
            headline_hash = self._get_headline_hash(story.title)
            self.headline_hashes.add(headline_hash)

        logger.info(
            "Deduplication index loaded: %d URL hashes, %d headline hashes, %d story IDs",
            len(self.url_hashes),
            len(self.headline_hashes),
            len(self.existing_story_ids),
        )

    def deduplicate_stories(
        self, stories: List[Story], enable_semantic: bool = False
    ) -> Tuple[List[Story], Dict[str, int]]:
        """
        Remove duplicate stories from the list.

        Args:
            stories: List of stories to deduplicate
            enable_semantic: Enable semantic deduplication (placeholder for future implementation)

        Returns:
            (unique_stories, dedup_stats)"""
        logger.info("Starting deduplication of %d stories", len(stories))

        unique_stories: List[Story] = []
        dedup_stats = {
            "total_input": len(stories),
            "duplicates_by_story_id": 0,
            "duplicates_by_url": 0,
            "duplicates_by_headline": 0,
            "duplicates_by_semantic": 0,  # Placeholder for future implementation
            "unique_output": 0,
        }

        # Track hashes for new stories to avoid duplicates within the same batch
        batch_url_hashes: Set[str] = set()
        batch_headline_hashes: Set[str] = set()
        batch_story_ids: Set[str] = set()

        for story in stories:
            is_duplicate = False
            duplicate_reason = ""

            # Check for story ID duplicates (existing and within batch)
            if story.story_id in self.existing_story_ids or story.story_id in batch_story_ids:
                is_duplicate = True
                duplicate_reason = "story_id"
                dedup_stats["duplicates_by_story_id"] += 1

            # Check for URL duplicates (skip Google News redirects)
            elif not self._is_google_news_redirect(story.url):
                url_hash = self._get_url_hash(story.url)
                if url_hash in self.url_hashes or url_hash in batch_url_hashes:
                    is_duplicate = True
                    duplicate_reason = "url"
                    dedup_stats["duplicates_by_url"] += 1
                else:
                    batch_url_hashes.add(url_hash)

            # Check for headline duplicates (if not already marked as duplicate)
            if not is_duplicate:
                headline_hash = self._get_headline_hash(story.title)
                if headline_hash in self.headline_hashes or headline_hash in batch_headline_hashes:
                    is_duplicate = True
                    duplicate_reason = "headline"
                    dedup_stats["duplicates_by_headline"] += 1
                else:
                    batch_headline_hashes.add(headline_hash)

            # Check for semantic duplicates (placeholder for future implementation)
            if not is_duplicate and enable_semantic:
                # TODO: Implement semantic deduplication
                # This would compare the current story against existing stories using NLP
                # Example implementation:                # is_semantic_dup, semantic_reason = self._is_semantically_duplicate(story, existing_stories)
                # if is_semantic_dup:
                #     is_duplicate = True
                #     duplicate_reason = "semantic"
                #     dedup_stats['duplicates_by_semantic'] += 1
                logger.debug("Semantic deduplication skipped (not implemented): %s...", story.title[:50])

            if is_duplicate:
                logger.debug("DUPLICATE (%s): %s... [%s]", duplicate_reason, story.title[:50], story.source)
            else:
                unique_stories.append(story)
                batch_story_ids.add(story.story_id)
                logger.debug("UNIQUE: %s... [%s]", story.title[:50], story.source)

        dedup_stats["unique_output"] = len(unique_stories)

        logger.info(
            "Deduplication complete: %d input stories, %d unique stories remaining",
            dedup_stats["total_input"],
            dedup_stats["unique_output"],
        )
        logger.info(
            "Removed duplicates: %d by story_id, %d by URL, %d by headline, %d by semantic",
            dedup_stats["duplicates_by_story_id"],
            dedup_stats["duplicates_by_url"],
            dedup_stats["duplicates_by_headline"],
            dedup_stats["duplicates_by_semantic"],
        )

        if enable_semantic:
            logger.info("Semantic deduplication was enabled but not implemented yet")

        return unique_stories, dedup_stats

    def _calculate_semantic_similarity(self, story1: Story, story2: Story) -> float:
        """
        Calculate semantic similarity between two stories using NLP.

        PLACEHOLDER: This method is intended for future implementation of
        advanced semantic deduplication using techniques like:
        - Sentence embeddings (e.g., BERT, SentenceTransformers)
        - TF-IDF cosine similarity
        - Named entity overlap
        - Topic modeling

        Args:
            story1: First story to compare
            story2: Second story to compare

        Returns:
            Similarity score between 0.0 and 1.0 (1.0 = identical)

        TODO: Implement semantic similarity calculation using:
        1. Pre-trained sentence embedding models
        2. Text preprocessing (stemming, stop word removal)
        3. Configurable similarity threshold
        4. Performance optimization for batch processing
        """  # Placeholder implementation - always returns 0.0 (no similarity)
        logger.debug(
            "Semantic similarity calculation not implemented - comparing '%s...' vs '%s...'",
            story1.title[:30],
            story2.title[:30],
        )
        return 0.0

    def _is_semantically_duplicate(
        self, story: Story, existing_stories: List[Story], threshold: float = 0.8
    ) -> Tuple[bool, str]:
        """
        Check if a story is semantically similar to any existing stories.

        PLACEHOLDER: This method is intended for future implementation of
        semantic deduplication that can catch stories with:
        - Different headlines but same content
        - Paraphrased versions of the same news
        - Stories from different angles about the same event

        Args:
            story: Story to check for semantic duplicates
            existing_stories: List of existing stories to compare against
            threshold: Similarity threshold above which stories are considered duplicates

        Returns:
            Tuple of (is_duplicate, reason_string)

        TODO: Implement using sentence embeddings and similarity metrics
        """  # Placeholder implementation - always returns False
        del existing_stories
        del threshold

        logger.debug("Semantic deduplication not implemented for story: '%s...'", story.title[:50])
        return False, "semantic_deduplication_not_implemented"
