from typing import List
from datetime import datetime, timedelta
from GoogleNews import GoogleNews  # Fixed import casing
from storage import Story

class GoogleNewsFetcher:
    def __init__(self, search_string: str, lookback_days: int = 1, language: str = "en"):
        self.search_string = search_string
        self.lookback_days = lookback_days
        self.language = language
        self.gn = GoogleNews(lang=language)

    def fetch(self) -> List[Story]:
        since = (datetime.now() - timedelta(days=self.lookback_days)).strftime("%m/%d/%Y")
        self.gn.set_time_range(since, datetime.now().strftime("%m/%d/%Y"))
        self.gn.search(self.search_string)
        results = self.gn.results(sort=True)
        stories = []
        for item in results:
            story = Story(
                story_id=item.get("link", "") or item.get("title", ""),
                title=item.get("title", ""),
                url=item.get("link", ""),
                date=item.get("date", ""),
                source=item.get("media", ""),
                byline=item.get("desc", None),
            )
            stories.append(story)
        return stories
