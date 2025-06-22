import logging
import hashlib
from typing import List
from GoogleNews import GoogleNews
from storage import Story

logger = logging.getLogger(__name__)


class GoogleNewsFetcher:
    """
    GoogleNewsFetcher fetches news stories from Google News based on a search string, lookback period, and language.
    Attributes:
        search_string (str): The search query to use for fetching news.
        lookback_days (int): Number of days to look back for news stories (default is 1).
        language (str): Language code for the news search (default is "en").
        gn (GoogleNews): Instance of the GoogleNews client for performing searches.
    Methods:
        fetch() -> List[Story]:
            Fetches news stories from Google News within the specified time range and search parameters.
            Returns a list of Story objects, each containing the story ID, title, URL, date, source, and byline.
            Handles errors gracefully and logs processing details.
    """

    def __init__(self, search_string: str, period: str = "1D", language: str = "en"):
        self.search_string = search_string
        self.period = period
        self.language = language
        self.gn = GoogleNews(lang=language)

        logger.info(
            "Initialized GoogleNewsFetcher with search_string='%s', period=%s, language='%s'",
            search_string,
            period,
            language,
        )

    def fetch(self) -> List[Story]:
        """Fetch news stories from Google News based on configured parameters."""

        logger.info("Fetching news for '%s' for period '%s' in language '%s'", self.search_string, self.period, self.language)

        try:
            self.gn.set_period(self.period)
            logger.debug("Set time range for Google News search")

            self.gn.search(self.search_string)
            logger.debug("Executed search for '%s'", self.search_string)

            results = self.gn.results(sort=True)
            logger.info("Retrieved %d raw results from Google News", len(results))

            stories: List[Story] = []
            for i, item in enumerate(results, 1):
                try:
                    title = item.get("title", "")
                    url = item.get("link", "")
                    date = item.get("date", "")
                    source = item.get("media", "")
                    byline = item.get("desc", None)

                    # Create a stable story_id based on title and source
                    # This avoids issues with changing Google redirect URLs
                    story_content = f"{title}:{source}".encode("utf-8")
                    story_id = hashlib.md5(story_content).hexdigest()

                    story = Story(
                        story_id=story_id,
                        title=title,
                        url=url,
                        date=date,
                        source=source,
                        byline=byline,
                    )
                    stories.append(story)

                    logger.debug("Processed story %d: '%s' from %s (ID: %s...)", i, title, source, story_id[:8])

                except Exception as e:
                    logger.warning("Failed to process story %d: %s", i, e)
                    logger.debug("Raw story data: %s", item)
                    continue

            logger.info("Successfully processed %d stories out of %d raw results", len(stories), len(results))
            return stories

        except Exception as e:
            logger.error("Error during Google News fetch: %s", e)
            raise
