"""
Summary generator for news articles using OpenAI integration.

Implements the summarization strategy defined in the PRD:
- If full text is empty: summary = headline
- If "video" in URL: summary = "Video: " + headline
- Else: summarize via OpenAI API
- Summary must be ≤ 300 characters including byline and source link
- Retry on character limit violations with emphasis on brevity
- Fallback to headline on OpenAI failures
"""

import logging
from typing import Optional, Dict, Any, Tuple

from openai import OpenAI, AuthenticationError
from storage import Story

logger = logging.getLogger(__name__)


class Summarizer:
    """Generate summaries for news articles using OpenAI with fallback strategies."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize summarizer with configuration.

        Args:
            config: Configuration dictionary containing:
                - api_key: OpenAI API key
                - max_length: Maximum summary length (default: 300)
                - retry_count: Number of retries for over-length summaries (default: 2)
                - model: OpenAI model to use (default: gpt-4o-mini)
        """
        self.config = config
        self.max_length = config.get("max_length", 300)
        self.retry_count = config.get("retry_count", 2)
        self.model = config.get("model", "gpt-4o-mini")
        self.client: Optional[OpenAI] = None

        # Initialize OpenAI client if available
        try:

            self.client = OpenAI(api_key=config["api_key"])
            models = self.client.models.list()  # Test API key validity
            # Check if the model is available
            if self.model not in [model.id for model in models.data]:
                raise KeyError(f"Model {self.model} not found in OpenAI models list")
            self.openai_enabled = True
            logger.info("Initialized Summarizer with OpenAI model: %s", self.model)
        except (KeyError, AuthenticationError):
            self.client = None
            self.openai_enabled = False
            logger.warning("OpenAI not available - using headline fallback only")

    def summarize_story(self, story: Story) -> tuple[str, bool]:
        """
        Generate a summary for a story following the PRD strategy.

        Args:
            story: Story object with title, url, full_text, byline, source

        Returns:
            Tuple of (summary_string, used_condensation) where summary_string is ≤ max_length characters including byline and source link
        """
        logger.info("Generating summary for story: %s", story.story_id)

        used_condensation = False

        # Check for video content
        if self._is_video_content(story.url):
            summary = f"Video: {story.title}"
            logger.debug("Detected video content, using video prefix")
        # Check if we have full text
        elif not story.full_text or len(story.full_text.strip()) < 50:
            summary = story.title
            logger.debug("No full text available, using headline")
        else:
            # Try OpenAI summarization with retries
            summary, used_condensation = self._generate_openai_summary(story)

        # Add byline and source link, ensuring total length ≤ max_length
        final_summary = self._format_final_summary(summary, story)

        logger.info("Generated summary (%d chars): %s...", len(final_summary), final_summary[:100])
        return final_summary, used_condensation

    def _is_video_content(self, url: str) -> bool:
        """Check if URL indicates video content."""
        if not url:
            return False

        video_indicators = [
            "youtube.com",
            "youtu.be",
            "vimeo.com",
            "twitch.tv",
            "dailymotion.com",
            "video.",
            "/video/",
            "/watch?v=",
            "/player/",
            "/embed/",
            "stream.",
            "play.",
        ]

        url_lower = url.lower()
        return any(indicator in url_lower for indicator in video_indicators)

    def _generate_openai_summary(self, story: Story) -> tuple[str, bool]:
        """
        Generate summary using OpenAI with retries for length violations.

        Args:
            story: Story object with full_text to summarize

        Returns:
            Tuple of (summary_text, used_condensation) - may fallback to headline if OpenAI fails
        """
        if not self.openai_enabled:
            return story.title, False

        # Calculate available characters for summary content
        # Per PRD: only count byline + source name + summary, not the URL
        byline_chars = 0
        if story.byline:
            clean_byline = story.byline.strip()
            if clean_byline.lower().startswith("by "):
                clean_byline = clean_byline[3:]
            byline_chars = len(f" By {clean_byline}.")

        source_chars = len(story.source) + 3  # " []" chars for markdown, URL doesn't count
        available_chars = self.max_length - byline_chars - source_chars - 5  # 5 char buffer for safety

        last_valid_summary = None
        for attempt in range(self.retry_count + 1):
            try:
                summary = self._call_openai_api(story, available_chars, attempt)

                if summary and len(summary) <= available_chars:
                    logger.debug("OpenAI summary generated successfully (attempt %d)", attempt + 1)
                    return summary, False
                if summary:
                    logger.warning(
                        "OpenAI summary too long: %d > %d chars (attempt %d)",
                        len(summary),
                        available_chars,
                        attempt + 1,
                    )
                    last_valid_summary = summary  # Keep the last summary for potential re-summarization
                else:
                    logger.warning("OpenAI returned empty summary (attempt %d)", attempt + 1)

            except RuntimeError as e:
                logger.warning("OpenAI API call failed (attempt %d): %s", attempt + 1, e)

        # Final attempt: re-summarize the last valid summary if we have one
        if last_valid_summary and self.openai_enabled:
            logger.info("Final attempt: re-summarizing the previous summary to fit character limit")
            try:
                condensed_summary = self._call_openai_api_on_summary(last_valid_summary, available_chars)
                if condensed_summary and len(condensed_summary) <= available_chars:
                    logger.debug("Successfully condensed summary to %d chars", len(condensed_summary))
                    return condensed_summary, True
                else:
                    logger.warning("Summary condensation failed or still too long")
            except RuntimeError as e:
                logger.warning("Summary condensation failed: %s", e)

        # All attempts failed, fallback to headline
        logger.warning("All OpenAI attempts failed, falling back to headline")
        return story.title, False

    def _call_openai_api(self, story: Story, max_chars: int, attempt: int) -> Optional[str]:
        """
        Make actual OpenAI API call with appropriate prompts.

        Args:
            story: Story to summarize
            max_chars: Maximum characters for summary
            attempt: Current attempt number (for prompt adjustment)

        Returns:
            Summary text or None if API call fails
        """
        # Adjust prompt based on attempt number for increasing brevity
        if attempt == 0:
            brevity_instruction = f"in under {max_chars} characters"
        elif attempt == 1:
            brevity_instruction = f"in under {max_chars} characters. Be very concise"
        else:
            brevity_instruction = f"in under {max_chars} characters. Be extremely brief and concise"

        system_prompt = (
            f"You are a news summarizer. Summarize the article {brevity_instruction}. "
            "Focus on the key facts and main points. Do not include bylines, source names, "
            "or URLs in your summary as they will be added separately."
        )

        user_prompt = (
            f"Article title: {story.title}\n\nArticle text: {(story.full_text or '')[:4000]}"  # Limit input length
        )

        try:
            if not self.client:
                raise RuntimeError("OpenAI client not initialized")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=min(150, max_chars // 3),  # Conservative token limit
                temperature=0.3,  # Lower temperature for more focused summaries
                timeout=30,
            )

            content = response.choices[0].message.content
            summary = content.strip() if content else ""
            logger.debug("OpenAI response (%d chars): %s...", len(summary), summary[:100])
            return summary

        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            raise RuntimeError(f"OpenAI API error: {e}") from e

    def _call_openai_api_on_summary(self, summary: str, max_chars: int) -> Optional[str]:
        """
        Make OpenAI API call to condense an existing summary.

        Args:
            summary: Previously generated summary to condense
            max_chars: Maximum characters for condensed summary

        Returns:
            Condensed summary text or None if API call fails
        """
        system_prompt = (
            f"You are a text condenser. Take the given summary and make it more concise "
            f"while keeping all key information. Output must be under {max_chars} characters. "
            "Be extremely brief and to the point."
        )

        user_prompt = f"Condense this summary: {summary}"

        try:
            if not self.client:
                raise RuntimeError("OpenAI client not initialized")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                max_tokens=min(100, max_chars // 3),  # Very conservative token limit
                temperature=0.1,  # Very low temperature for focused condensation
                timeout=30,
            )

            content = response.choices[0].message.content
            condensed_summary = content.strip() if content else ""
            logger.debug(
                "OpenAI condensation response (%d chars): %s...", len(condensed_summary), condensed_summary[:100]
            )
            return condensed_summary

        except Exception as e:
            logger.error("OpenAI condensation API error: %s", e)
            raise

    def _format_final_summary(self, summary: str, story: Story) -> str:
        """
        Format final summary with byline and source link, ensuring length compliance.

        Args:
            summary: Base summary text
            story: Story object with byline and source info

        Returns:
            Final formatted summary ≤ max_length characters
        """
        # Prepare byline - clean up any duplicate "By" prefixes
        byline = ""
        if story.byline:
            clean_byline = story.byline.strip()
            # Remove "By " prefix if it exists since we'll add it ourselves
            if clean_byline.lower().startswith("by "):
                clean_byline = clean_byline[3:]
            byline = f" By {clean_byline}."

        # Prepare source link in proper Markdown format
        # Per PRD: only source name counts toward character limit, not the URL
        source_url = story.decoded_url or story.url
        source_link = f" [{story.source}]({source_url})"

        # Calculate character limit: only count source name + byline + summary, not the URL
        # Characters that count toward limit: summary + byline + " [" + source_name + "]"
        counted_metadata_chars = len(byline) + len(story.source) + 3  # " []" chars for markdown
        available_for_summary = self.max_length - counted_metadata_chars

        # Truncate summary if needed (last resort)
        if len(summary) > available_for_summary:
            summary = summary[: available_for_summary - 3] + "..."
            logger.warning(
                "Summary truncated to fit character limit: %d + %d = %d",
                len(summary),
                counted_metadata_chars,
                len(summary) + counted_metadata_chars,
            )
        # Combine all parts (full URL is appended but doesn't count toward limit)
        final_summary = summary + byline + source_link

        # Character limit check - only count the parts that matter per PRD
        counted_chars = len(summary) + len(byline) + len(story.source) + 3  # " ()" chars
        if counted_chars > self.max_length:
            # Emergency truncation (shouldn't happen with proper calculations)
            available_for_summary_emergency = (
                self.max_length - len(byline) - len(story.source) - 3 - 3
            )  # extra 3 for "..."
            summary = summary[:available_for_summary_emergency] + "..."
            final_summary = summary + byline + source_link
            logger.error(
                "Emergency truncation applied: counted chars = %d, new summary length = %d", counted_chars, len(summary)
            )

        logger.debug("Summary formatting - Total length: %d, Counted chars: %d", len(final_summary), counted_chars)
        return final_summary

    def summarize_stories(self, stories: list[Story]) -> Tuple[list[Story], Dict[str, Any]]:
        """
        Generate summaries for multiple stories.

        Args:
            stories: List of Story objects to summarize

        Returns:
            Tuple of (updated_stories, summarization_stats)
        """
        logger.info("Starting summarization for %d stories", len(stories))

        stats = {
            "total_stories": len(stories),
            "summarized": 0,
            "used_openai": 0,
            "used_condensation": 0,
            "used_headline": 0,
            "used_video_prefix": 0,
            "failed": 0,
        }

        updated_stories: list[Story] = []

        for i, story in enumerate(stories, 1):
            try:
                # Skip if already has summary
                if story.summary:
                    logger.debug("Story %d: Already has summary, skipping", i)
                    updated_stories.append(story)
                    continue

                # Generate summary using the main summarize_story method
                logger.debug("Story %d: Generating summary for %s", i, story.story_id)

                summary, used_condensation = self.summarize_story(story)

                # Update story
                story.summary = summary
                updated_stories.append(story)

                # Update stats based on what happened
                stats["summarized"] += 1
                if self._is_video_content(story.url):
                    stats["used_video_prefix"] += 1
                elif self.openai_enabled and story.full_text and len(story.full_text.strip()) >= 50:
                    if used_condensation:
                        stats["used_condensation"] += 1
                    else:
                        stats["used_openai"] += 1
                else:
                    stats["used_headline"] += 1

            except (RuntimeError, AuthenticationError, KeyError) as e:
                logger.error("Error summarizing story %d (%s): %s", i, story.story_id, e)
                story.summary = story.title  # Fallback to headline
                updated_stories.append(story)
                stats["failed"] += 1

        logger.info(
            "Summarization complete: %d summarized, %d used OpenAI, %d used condensation, %d used headline, %d used video prefix, %d failed",
            stats["summarized"],
            stats["used_openai"],
            stats["used_condensation"],
            stats["used_headline"],
            stats["used_video_prefix"],
            stats["failed"],
        )

        return updated_stories, stats
