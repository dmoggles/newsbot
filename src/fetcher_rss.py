import logging
import hashlib
from typing import List
from datetime import datetime, timedelta
from GoogleNews import GoogleNews
from storage import Story

logger = logging.getLogger(__name__)

class GoogleNewsFetcher:
    def __init__(self, search_string: str, lookback_days: int = 1, language: str = "en", country: str = "US"):
        self.search_string = search_string
        self.lookback_days = lookback_days
        self.language = language
        self.country = country
        
        # Initialize GoogleNews with get_news functionality
        self.gn = GoogleNews(lang=language)
        
        logger.info(f"Initialized GoogleNewsFetcher with search_string='{search_string}', lookback_days={lookback_days}, language='{language}', country='{country}'")

    def _is_google_news_url(self, url: str) -> bool:
        """Check if a URL is a Google News redirect URL that needs decoding."""
        if not url:
            return False
        return 'news.google.com' in url and ('read/CBM' in url or 'articles/CBM' in url or 'articles/CAI' in url)

    def fetch(self) -> List[Story]:
        """Fetch news stories from Google News using get_news() and decode redirect URLs."""
        logger.info(f"Fetching news for '{self.search_string}' using GoogleNews.get_news()")
        
        try:
            # Set time range if needed
            if self.lookback_days > 0:
                since = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%m/%d/%Y")
                until = datetime.now().strftime("%m/%d/%Y")
                logger.debug(f"Setting time range: {since} to {until}")
                self.gn.set_time_range(since, until)
            
            # Use get_news to get Google News URLs (not final destination URLs)
            logger.debug("Calling GoogleNews.get_news()...")
            self.gn.get_news(key=self.search_string)
            
            # Get results
            results = self.gn.results(sort=True)
            logger.info(f"Retrieved {len(results)} raw results from GoogleNews.get_news()")
            
            stories = []
            
            for i, item in enumerate(results, 1):
                try:
                    title = item.get("title", "")
                    google_news_url = item.get("link", "")  # This should be a Google News URL
                    date = item.get("date", "")
                    media = item.get("media", "")  # Source from GoogleNews
                    site = item.get("site", "")    # Alternative source field
                    desc = item.get("desc", "")    # Description
                    reporter = item.get("reporter", "")  # Reporter/byline
                    
                    # Use media or site as source
                    source = media or site or ""
                    
                    # Use reporter as byline
                    byline = reporter if reporter else None
                    
                    logger.debug(f"Processing item {i}: {title}")
                    logger.debug(f"  Google News URL: {google_news_url}")
                    logger.debug(f"  Source: {source}")
                    
                    # Check if we got a Google News URL but don't decode it yet
                    # URL decoding will be done later in the pipeline after filtering
                    is_google_url = self._is_google_news_url(google_news_url)
                    
                    if not google_news_url:
                        logger.warning(f"Item {i}: No URL available, skipping")
                        continue
                    
                    if is_google_url:
                        logger.debug("  -> Google News URL detected (will decode later)")
                        # Store the Google News URL as the main URL for now
                        final_url = google_news_url
                        google_redirect_url = google_news_url
                    else:
                        logger.debug("  -> Direct URL (no decoding needed)")
                        final_url = google_news_url
                        google_redirect_url = None
                    
                    # Create a stable story_id based on title and source
                    story_content = f"{title}:{source}".encode('utf-8')
                    story_id = hashlib.md5(story_content).hexdigest()
                    
                    # Create Story object
                    story = Story(
                        story_id=story_id,
                        title=title,
                        url=final_url,  # Store the URL (will be Google News URL or direct URL)
                        date=date,
                        source=source,
                        byline=byline,
                        google_redirect_url=google_redirect_url,  # Store Google redirect URL if present
                        description=desc
                    )
                    
                    stories.append(story)
                    
                    logger.debug(f"Processed story {i}: '{title}' from {source} (ID: {story_id[:8]}...)")
                    
                except Exception as e:
                    logger.warning(f"Failed to process item {i}: {e}")
                    logger.debug(f"Raw item data: {item}")
                    continue
            
            logger.info(f"Successfully processed {len(stories)} stories from GoogleNews.get_news()")
            return stories
            
        except Exception as e:
            logger.error(f"Error during Google News fetch with get_news(): {e}")
            raise
