import logging
import hashlib
from typing import List, Dict, Any
from GoogleNews import GoogleNews
from storage import Story

logger = logging.getLogger(__name__)


class GoogleNewsFetcher:
    """
    GoogleNewsFetcher fetches news stories from Google News using the get_news() method,
    optionally within a specified lookback period, language, and country.
    Attributes:
        search_string (str): The search query to use for fetching news.
        period (str): Lookback period for news articles (default: '1D' for 1 day).
        language (str): Language code for news articles (default: "en").
        region (str): Region code for news articles (default: "UK").
        gn (GoogleNews): Instance of the GoogleNews class for fetching news.
    Methods:
        __init__(search_string: str, lookback_days: int = 1, language: str = "en", region: str = "UK"):
            Initializes the fetcher with the given search string, lookback period, language, and country.
        _is_google_news_url(url: str) -> bool:
            Checks if a given URL is a Google News redirect URL that may need decoding.
        fetch() -> List[Story]:
            Fetches news stories from Google News using the get_news() method, processes the results,
            and returns a list of Story objects. Google News redirect URLs are detected and stored for
            later decoding in the pipeline.
    """

    def __init__(self, search_string: str, period: str = '1D', language: str = "en", region: str = "uk"):
        self.search_string = search_string
        self.period = period
        self.language = language
        self.region = region

        # Initialize GoogleNews with get_news functionality
        self.gn = GoogleNews(lang=language, region=region)

        logger.info(
            "Initialized GoogleNewsFetcher with search_string='%s', period=%s, language='%s', region='%s'",
            search_string,
            period,
            language,
            region,
        )

    def _is_google_news_url(self, url: str) -> bool:
        """Check if a URL is a Google News redirect URL that needs decoding."""
        if not url:
            return False
        return "news.google.com" in url and ("read/CBM" in url or "articles/CBM" in url or "articles/CAI" in url)

    def _setup_time_range(self) -> None:
        """Set up the time range for Google News search if lookback_days is specified."""
        if self.period:
            logger.debug("Setting up time range for Google News: period='%s'", self.period)
            self.gn.set_period(self.period)

    def _fetch_raw_results(self) -> List[Dict[str, Any]]:
        """Fetch raw results from Google News."""
        logger.debug("Calling GoogleNews.get_news()...")
        self.gn.get_news(key=self.search_string)

        results = self.gn.results(sort=True)
        logger.info("Retrieved %d raw results from GoogleNews.get_news()", len(results))
        return results

    def _process_single_item(self, i: int, item: Dict[str, Any]) -> Story:
        """Process a single news item into a Story object.

        Args:
            i: Item index (1-based) for logging purposes
            item: Raw item dictionary from Google News

        Returns:
            Story object

        Raises:
            ValueError: If the item cannot be processed (e.g., missing URL)
        """
        title = item.get("title", "")
        google_news_url = item.get("link", "")
        date = item.get("date", "")
        media = item.get("media", "")
        site = item.get("site", "")
        desc = item.get("desc", "")
        reporter = item.get("reporter", "")

        # Use media or site as source
        source = media or site or ""
        # Use reporter as byline
        byline = reporter if reporter else None

        logger.debug("Processing item %d: %s", i, title)
        logger.debug("  Google News URL: %s", google_news_url)
        logger.debug("  Source: %s", source)

        if not google_news_url:
            logger.warning("Item %d: No URL available, skipping", i)
            raise ValueError("No URL available")

        # Determine URL handling
        is_google_url = self._is_google_news_url(google_news_url)
        if is_google_url:
            logger.debug("  -> Google News URL detected (will decode later)")
            final_url = google_news_url
            google_redirect_url = google_news_url
        else:
            logger.debug("  -> Direct URL (no decoding needed)")
            final_url = google_news_url
            google_redirect_url = None

        # Create stable story ID
        story_content = f"{title}:{source}".encode("utf-8")
        story_id = hashlib.md5(story_content).hexdigest()

        # Create Story object
        story = Story(
            story_id=story_id,
            title=title,
            url=final_url,
            date=date,
            source=source,
            byline=byline,
            google_redirect_url=google_redirect_url,
            description=desc,
        )

        logger.debug("Processed story %d: '%s' from %s (ID: %s...)", i, title, source, story_id[:8])
        return story

    def _process_all_items(self, results: List[Dict[str, Any]]) -> List[Story]:
        """Process all news items from Google News results.

        Args:
            results: List of raw item dictionaries from Google News

        Returns:
            List of successfully processed Story objects
        """
        stories: List[Story] = []

        for i, item in enumerate(results, 1):
            try:
                story = self._process_single_item(i, item)
                stories.append(story)
            except (ValueError, Exception) as e:
                logger.warning("Failed to process item %d: %s", i, e)
                logger.debug("Raw item data: %s", item)
                continue

        return stories

    def fetch(self) -> List[Story]:
        """Fetch news stories from Google News using get_news() and decode redirect URLs."""
        logger.info("Fetching news for '%s' using GoogleNews.get_news()", self.search_string)

        try:
            # Setup time range
            self._setup_time_range()

            # Fetch raw results from Google News
            results = self._fetch_raw_results()

            # Process all items into Story objects
            stories = self._process_all_items(results)

            logger.info("Successfully processed %d stories from GoogleNews.get_news()", len(stories))
            return stories

        except Exception as e:
            logger.error("Error during Google News fetch with get_news(): %s", e)
            raise
