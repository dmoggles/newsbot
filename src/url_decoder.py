import logging
from typing import List, Optional, Dict, Any
from googlenewsdecoder import new_decoderv1 # type: ignore
from storage import Story

logger = logging.getLogger(__name__)

class URLDecoder:
    """Handles decoding of Google News redirect URLs to actual article URLs."""
    
    def __init__(self) -> None:
        logger.info("Initialized URL Decoder")
    
    def _decode_google_news_url(self, url: str) -> Optional[str]:
        """Decode a Google News redirect URL to the actual article URL."""
        try:
            logger.debug("Attempting to decode Google News URL: %s...", url[:100])
            
            result: Dict[str, Any] = new_decoderv1(url) # type: ignore
            
            if result.get('status'):
                decoded_url = result.get('decoded_url')
                logger.debug("Successfully decoded URL: %s", decoded_url)
                return decoded_url
            
            error_msg = result.get('message', 'Unknown error')
            logger.warning("Failed to decode Google News URL: %s", error_msg)
            return None
                
        except Exception as e: # pylint: disable=broad-except
            logger.warning("Exception while decoding Google News URL: %s", e)
            return None
    
    def _is_google_news_url(self, url: str) -> bool:
        """Check if a URL is a Google News redirect URL that needs decoding."""
        if not url:
            return False
        return 'news.google.com' in url and ('read/CBM' in url or 'articles/CBM' in url or 'articles/CAI' in url)
    
    def decode_stories(self, stories: List[Story]) -> tuple[List[Story], Dict[str, int]]:
        """
        Decode Google News URLs in stories.
        Returns (updated_stories, decode_stats)
        """
        logger.info("Starting URL decoding for %d stories", len(stories))
        
        decode_stats = {
            "total_stories": len(stories),
            "google_urls_found": 0,
            "successfully_decoded": 0,
            "decode_failures": 0,
            "direct_urls": 0
        }
        
        updated_stories: List[Story] = []
        
        for i, story in enumerate(stories, 1):
            try:
                # Check if this story has a Google News URL that needs decoding
                if story.google_redirect_url and self._is_google_news_url(story.google_redirect_url):
                    decode_stats["google_urls_found"] += 1
                    logger.debug("Story %d: Decoding Google News URL", i)
                    
                    # Decode the URL
                    decoded_url = self._decode_google_news_url(story.google_redirect_url)
                    
                    if decoded_url:
                        # Update the story with the decoded URL
                        story.url = decoded_url
                        decode_stats["successfully_decoded"] += 1
                        logger.debug("Story %d: Successfully decoded URL", i)
                    else:
                        # Keep the original Google News URL if decoding failed
                        decode_stats["decode_failures"] += 1
                        logger.warning("Story %d: Failed to decode URL, keeping original", i)
                
                elif self._is_google_news_url(story.url):
                    # The main URL is a Google News URL (no separate redirect URL stored)
                    decode_stats["google_urls_found"] += 1
                    logger.debug("Story %d: Main URL is Google News URL, decoding", i)
                    
                    decoded_url = self._decode_google_news_url(story.url)
                    
                    if decoded_url:
                        # Store original URL in google_redirect_url and update main URL
                        story.google_redirect_url = story.url
                        story.url = decoded_url
                        decode_stats["successfully_decoded"] += 1
                        logger.debug("Story %d: Successfully decoded main URL", i)
                    else:
                        decode_stats["decode_failures"] += 1
                        logger.warning("Story %d: Failed to decode main URL", i)
                
                else:
                    # Direct URL, no decoding needed
                    decode_stats["direct_urls"] += 1
                    logger.debug("Story %d: Direct URL, no decoding needed", i)
                
                updated_stories.append(story)
                
            except Exception as e: # pylint: disable=broad-except
                logger.error("Error processing story %d for URL decoding: %s", i, e)
                # Add the story without modification if there's an error
                updated_stories.append(story)
                decode_stats["decode_failures"] += 1
        
        logger.info(
            "URL decoding complete: %d decoded, %d failed, %d direct URLs",
            decode_stats['successfully_decoded'],
            decode_stats['decode_failures'],
            decode_stats['direct_urls']
        )
        
        return updated_stories, decode_stats
