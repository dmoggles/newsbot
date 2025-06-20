import logging
from typing import List, Optional
from googlenewsdecoder import new_decoderv1
from storage import Story

logger = logging.getLogger(__name__)

class URLDecoder:
    """Handles decoding of Google News redirect URLs to actual article URLs."""
    
    def __init__(self):
        logger.info("Initialized URL Decoder")
    
    def _decode_google_news_url(self, url: str) -> Optional[str]:
        """Decode a Google News redirect URL to the actual article URL."""
        try:
            logger.debug(f"Attempting to decode Google News URL: {url[:100]}...")
            
            result = new_decoderv1(url)
            
            if result.get('status'):
                decoded_url = result.get('decoded_url')
                logger.debug(f"Successfully decoded URL: {decoded_url}")
                return decoded_url
            else:
                error_msg = result.get('message', 'Unknown error')
                logger.warning(f"Failed to decode Google News URL: {error_msg}")
                return None
                
        except Exception as e:
            logger.warning(f"Exception while decoding Google News URL: {e}")
            return None
    
    def _is_google_news_url(self, url: str) -> bool:
        """Check if a URL is a Google News redirect URL that needs decoding."""
        if not url:
            return False
        return 'news.google.com' in url and ('read/CBM' in url or 'articles/CBM' in url or 'articles/CAI' in url)
    
    def decode_stories(self, stories: List[Story]) -> tuple[List[Story], dict]:
        """
        Decode Google News URLs in stories.
        Returns (updated_stories, decode_stats)
        """
        logger.info(f"Starting URL decoding for {len(stories)} stories")
        
        decode_stats = {
            "total_stories": len(stories),
            "google_urls_found": 0,
            "successfully_decoded": 0,
            "decode_failures": 0,
            "direct_urls": 0
        }
        
        updated_stories = []
        
        for i, story in enumerate(stories, 1):
            try:
                # Check if this story has a Google News URL that needs decoding
                if story.google_redirect_url and self._is_google_news_url(story.google_redirect_url):
                    decode_stats["google_urls_found"] += 1
                    logger.debug(f"Story {i}: Decoding Google News URL")
                    
                    # Decode the URL
                    decoded_url = self._decode_google_news_url(story.google_redirect_url)
                    
                    if decoded_url:
                        # Update the story with the decoded URL
                        story.url = decoded_url
                        decode_stats["successfully_decoded"] += 1
                        logger.debug(f"Story {i}: Successfully decoded URL")
                    else:
                        # Keep the original Google News URL if decoding failed
                        decode_stats["decode_failures"] += 1
                        logger.warning(f"Story {i}: Failed to decode URL, keeping original")
                
                elif self._is_google_news_url(story.url):
                    # The main URL is a Google News URL (no separate redirect URL stored)
                    decode_stats["google_urls_found"] += 1
                    logger.debug(f"Story {i}: Main URL is Google News URL, decoding")
                    
                    decoded_url = self._decode_google_news_url(story.url)
                    
                    if decoded_url:
                        # Store original URL in google_redirect_url and update main URL
                        story.google_redirect_url = story.url
                        story.url = decoded_url
                        decode_stats["successfully_decoded"] += 1
                        logger.debug(f"Story {i}: Successfully decoded main URL")
                    else:
                        decode_stats["decode_failures"] += 1
                        logger.warning(f"Story {i}: Failed to decode main URL")
                
                else:
                    # Direct URL, no decoding needed
                    decode_stats["direct_urls"] += 1
                    logger.debug(f"Story {i}: Direct URL, no decoding needed")
                
                updated_stories.append(story)
                
            except Exception as e:
                logger.error(f"Error processing story {i} for URL decoding: {e}")
                # Add the story without modification if there's an error
                updated_stories.append(story)
                decode_stats["decode_failures"] += 1
        
        logger.info(f"URL decoding complete: {decode_stats['successfully_decoded']} decoded, "
                   f"{decode_stats['decode_failures']} failed, {decode_stats['direct_urls']} direct URLs")
        
        return updated_stories, decode_stats
