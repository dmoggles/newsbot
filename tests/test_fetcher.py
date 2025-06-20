from fetcher import GoogleNewsFetcher
from storage import Story

def test_fetcher_returns_stories(monkeypatch):
    # Mock GoogleNews methods
    class MockGoogleNews:
        def __init__(self, lang):
            pass
        def set_time_range(self, since, until):
            pass
        def search(self, search_string):
            pass
        def results(self, sort=True):
            return [
                {
                    "title": "Test Title",
                    "link": "http://example.com/story",
                    "date": "06/20/2025",
                    "media": "Test Source",
                    "desc": "Byline text",
                }
            ]
    monkeypatch.setattr("fetcher.GoogleNews", MockGoogleNews)
    fetcher = GoogleNewsFetcher(search_string="test", lookback_days=1, language="en")
    stories = fetcher.fetch()
    assert len(stories) == 1
    story = stories[0]
    assert isinstance(story, Story)
    assert story.title == "Test Title"
    assert story.url == "http://example.com/story"
    assert story.source == "Test Source"
    assert story.byline == "Byline text"
