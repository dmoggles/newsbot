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

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available - install with: pip install openai")

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
        self.max_length = config.get('max_length', 300)
        self.retry_count = config.get('retry_count', 2)
        self.model = config.get('model', 'gpt-4o-mini')
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE and config.get('api_key'):
            self.client = OpenAI(api_key=config['api_key'])
            self.openai_enabled = True
            logger.info(f"Initialized Summarizer with OpenAI model: {self.model}")
        else:
            self.client = None
            self.openai_enabled = False
            logger.warning("OpenAI not available - using headline fallback only")
    
    def summarize_story(self, story: Story) -> str:
        """
        Generate a summary for a story following the PRD strategy.
        
        Args:
            story: Story object with title, url, full_text, byline, source
            
        Returns:
            Summary string ≤ max_length characters including byline and source link
        """
        logger.info(f"Generating summary for story: {story.story_id}")
        
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
            summary, _ = self._generate_openai_summary(story)  # Don't store condensation info on story
        
        # Add byline and source link, ensuring total length ≤ max_length
        final_summary = self._format_final_summary(summary, story)
        
        logger.info(f"Generated summary ({len(final_summary)} chars): {final_summary[:100]}...")
        return final_summary
    
    def _is_video_content(self, url: str) -> bool:
        """Check if URL indicates video content."""
        if not url:
            return False
        
        video_indicators = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv',
            'dailymotion.com', 'video.', '/video/', '/watch?v=',
            '/player/', '/embed/', 'stream.', 'play.'
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
                    logger.debug(f"OpenAI summary generated successfully (attempt {attempt + 1})")
                    return summary, False
                elif summary:
                    logger.warning(f"OpenAI summary too long: {len(summary)} > {available_chars} chars (attempt {attempt + 1})")
                    last_valid_summary = summary  # Keep the last summary for potential re-summarization
                else:
                    logger.warning(f"OpenAI returned empty summary (attempt {attempt + 1})")
                    
            except Exception as e:
                logger.warning(f"OpenAI API call failed (attempt {attempt + 1}): {e}")
        
        # Final attempt: re-summarize the last valid summary if we have one
        if last_valid_summary and self.openai_enabled:
            logger.info("Final attempt: re-summarizing the previous summary to fit character limit")
            try:
                condensed_summary = self._call_openai_api_on_summary(last_valid_summary, available_chars)
                if condensed_summary and len(condensed_summary) <= available_chars:
                    logger.debug(f"Successfully condensed summary to {len(condensed_summary)} chars")
                    return condensed_summary, True
                else:
                    logger.warning(f"Summary condensation failed or still too long")
            except Exception as e:
                logger.warning(f"Summary condensation failed: {e}")
        
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
        
        user_prompt = f"Article title: {story.title}\n\nArticle text: {(story.full_text or '')[:4000]}"  # Limit input length
        
        try:
            if not self.client:
                raise Exception("OpenAI client not initialized")
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=min(150, max_chars // 3),  # Conservative token limit
                temperature=0.3,  # Lower temperature for more focused summaries
                timeout=30
            )
            
            content = response.choices[0].message.content
            summary = content.strip() if content else ""
            logger.debug(f"OpenAI response ({len(summary)} chars): {summary[:100]}...")
            return summary
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
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
                raise Exception("OpenAI client not initialized")
                
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=min(100, max_chars // 3),  # Very conservative token limit
                temperature=0.1,  # Very low temperature for focused condensation
                timeout=30
            )
            
            content = response.choices[0].message.content
            condensed_summary = content.strip() if content else ""
            logger.debug(f"OpenAI condensation response ({len(condensed_summary)} chars): {condensed_summary[:100]}...")
            return condensed_summary
            
        except Exception as e:
            logger.error(f"OpenAI condensation API error: {e}")
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
            summary = summary[:available_for_summary - 3] + "..."
            logger.warning(f"Summary truncated to fit character limit: {len(summary)} + {counted_metadata_chars} = {len(summary) + counted_metadata_chars}")
        
        # Combine all parts (full URL is appended but doesn't count toward limit)
        final_summary = summary + byline + source_link
        
        # Character limit check - only count the parts that matter per PRD
        counted_chars = len(summary) + len(byline) + len(story.source) + 3  # " ()" chars
        if counted_chars > self.max_length:
            # Emergency truncation (shouldn't happen with proper calculations)
            available_for_summary_emergency = self.max_length - len(byline) - len(story.source) - 3 - 3  # extra 3 for "..."
            summary = summary[:available_for_summary_emergency] + "..."
            final_summary = summary + byline + source_link
            logger.error(f"Emergency truncation applied: counted chars = {counted_chars}, new summary length = {len(summary)}")
        
        logger.debug(f"Summary formatting - Total length: {len(final_summary)}, Counted chars: {counted_chars}")
        return final_summary
    
    def summarize_stories(self, stories: list[Story]) -> Tuple[list[Story], Dict[str, Any]]:
        """
        Generate summaries for multiple stories.
        
        Args:
            stories: List of Story objects to summarize
            
        Returns:
            Tuple of (updated_stories, summarization_stats)
        """
        logger.info(f"Starting summarization for {len(stories)} stories")
        
        stats = {
            "total_stories": len(stories),
            "summarized": 0,
            "used_openai": 0,
            "used_condensation": 0,
            "used_headline": 0,
            "used_video_prefix": 0,
            "failed": 0
        }
        
        updated_stories = []
        condensation_used_stories = set()  # Track which stories used condensation
        
        for i, story in enumerate(stories, 1):
            try:
                # Skip if already has summary
                if story.summary:
                    logger.debug(f"Story {i}: Already has summary, skipping")
                    updated_stories.append(story)
                    continue
                
                # Generate summary
                logger.debug(f"Story {i}: Generating summary for {story.story_id}")
                
                # Track condensation usage for this story
                if self._is_video_content(story.url):
                    summary = f"Video: {story.title}"
                    logger.debug("Detected video content, using video prefix")
                elif not story.full_text or len(story.full_text.strip()) < 50:
                    summary = story.title
                    logger.debug("No full text available, using headline")
                else:
                    # Try OpenAI summarization with retries
                    summary, used_condensation = self._generate_openai_summary(story)
                    if used_condensation:
                        condensation_used_stories.add(story.story_id)
                
                # Update story
                story.summary = summary
                updated_stories.append(story)
                
                # Update stats
                stats["summarized"] += 1
                if self._is_video_content(story.url):
                    stats["used_video_prefix"] += 1
                elif self.openai_enabled and story.full_text and len(story.full_text.strip()) >= 50:
                    if story.story_id in condensation_used_stories:
                        stats["used_condensation"] += 1
                    else:
                        stats["used_openai"] += 1
                else:
                    stats["used_headline"] += 1
                
            except Exception as e:
                logger.error(f"Error summarizing story {i} ({story.story_id}): {e}")
                story.summary = story.title  # Fallback to headline
                updated_stories.append(story)
                stats["failed"] += 1
        
        logger.info(f"Summarization complete: {stats['summarized']} summarized, "
                   f"{stats['used_openai']} used OpenAI, {stats['used_condensation']} used condensation, "
                   f"{stats['used_headline']} used headline, {stats['used_video_prefix']} used video prefix, "
                   f"{stats['failed']} failed")
        
        return updated_stories, stats
