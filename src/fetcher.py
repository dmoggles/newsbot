import logging
from typing import List
from datetime import datetime, timedelta
from GoogleNews import GoogleNews  # Fixed import casing
from storage import Story

logger = logging.getLogger(__name__)

class GoogleNewsFetcher:
    def __init__(self, search_string: str, lookback_days: int = 1, language: str = "en"):
        self.search_string = search_string
        self.lookback_days = lookback_days
        self.language = language
        self.gn = GoogleNews(lang=language)
        
        logger.info(f"Initialized GoogleNewsFetcher with search_string='{search_string}', lookback_days={lookback_days}, language='{language}'")

    def fetch(self) -> List[Story]:
        """Fetch news stories from Google News based on configured parameters."""
        since = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%m/%d/%Y")
        until = datetime.now().strftime("%m/%d/%Y")
        
        logger.info(f"Fetching news for '{self.search_string}' from {since} to {until}")
        
        try:
            self.gn.set_time_range(since, until)  # type: ignore
            logger.debug("Set time range for Google News search")
            
            self.gn.search(self.search_string)  # type: ignore
            logger.debug(f"Executed search for '{self.search_string}'")
            
            results = self.gn.results(sort=True)  # type: ignore
            logger.info(f"Retrieved {len(results)} raw results from Google News")
            
            stories = []
            for i, item in enumerate(results, 1):
                try:
                    story_id = item.get("link", "") or item.get("title", "")  # type: ignore
                    title = item.get("title", "")  # type: ignore
                    url = item.get("link", "")  # type: ignore
                    date = item.get("date", "")  # type: ignore
                    source = item.get("media", "")  # type: ignore
                    byline = item.get("desc", None)  # type: ignore
                    
                    story = Story(
                        story_id=story_id,
                        title=title,
                        url=url,
                        date=date,
                        source=source,
                        byline=byline,
                    )
                    stories.append(story)
                    
                    logger.debug(f"Processed story {i}: '{title}' from {source}")
                    
                except Exception as e:
                    logger.warning(f"Failed to process story {i}: {e}")
                    logger.debug(f"Raw story data: {item}")
                    continue
            
            logger.info(f"Successfully processed {len(stories)} stories out of {len(results)} raw results")
            return stories
            
        except Exception as e:
            logger.error(f"Error during Google News fetch: {e}")
            raise
