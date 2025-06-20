from src.filter import StoryFilter
from src.storage import Story

class TestStoryFilter:
    """Test cases for the StoryFilter class."""
    
    def test_initialization(self):
        """Test filter initialization with configuration."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News", "Reuters"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor", "gossip"],
                "banned_url_keywords": ["clickbait", "youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        assert filter_obj.confirmed_sources == {"BBC News", "Reuters"}
        assert filter_obj.accepted_sources == {"The Guardian"}
        assert filter_obj.banned_headline_keywords == ["rumor", "gossip"]
        assert filter_obj.banned_url_keywords == ["clickbait", "youtube"]
    
    def test_initialization_empty_config(self):
        """Test filter initialization with empty configuration."""
        config = {}
        
        filter_obj = StoryFilter(config)
        
        assert filter_obj.confirmed_sources == set()
        assert filter_obj.accepted_sources == set()
        assert filter_obj.banned_headline_keywords == []
        assert filter_obj.banned_url_keywords == []
    
    def test_is_source_allowed_confirmed(self):
        """Test source filtering for confirmed sources."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News", "Reuters"],
                "accepted_sources": ["The Guardian"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        # Test confirmed source (case insensitive)
        is_allowed, source_type = filter_obj.is_source_allowed("BBC News")
        assert is_allowed
        assert source_type == "confirmed"
        
        # Test confirmed source with different casing
        is_allowed, source_type = filter_obj.is_source_allowed("bbc news")
        assert is_allowed
        assert source_type == "confirmed"
        
        # Test partial match
        is_allowed, source_type = filter_obj.is_source_allowed("BBC News International")
        assert is_allowed
        assert source_type == "confirmed"
    
    def test_is_source_allowed_accepted(self):
        """Test source filtering for accepted sources."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian", "NY Times"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        # Test accepted source
        is_allowed, source_type = filter_obj.is_source_allowed("The Guardian")
        assert is_allowed
        assert source_type == "accepted"
        
        # Test case insensitive
        is_allowed, source_type = filter_obj.is_source_allowed("ny times")
        assert is_allowed
        assert source_type == "accepted"
    
    def test_is_source_allowed_banned(self):
        """Test source filtering for banned sources."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        # Test banned source
        is_allowed, source_type = filter_obj.is_source_allowed("Random Blog")
        assert not is_allowed
        assert source_type == "banned"
        
        # Test empty source
        is_allowed, source_type = filter_obj.is_source_allowed("")
        assert not is_allowed
        assert source_type == "empty"
    
    def test_has_banned_headline_keywords(self):
        """Test headline keyword filtering."""
        config = {
            "filter": {
                "banned_headline_keywords": ["rumor", "gossip", "fake"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        # Test clean headline
        has_banned, keywords = filter_obj.has_banned_headline_keywords("Chelsea wins match")
        assert not has_banned
        assert keywords == []
        
        # Test headline with banned keyword
        has_banned, keywords = filter_obj.has_banned_headline_keywords("Chelsea transfer rumor emerges")
        assert has_banned
        assert "rumor" in keywords
        
        # Test case insensitive
        has_banned, keywords = filter_obj.has_banned_headline_keywords("GOSSIP: Chelsea news")
        assert has_banned
        assert "gossip" in keywords
        
        # Test multiple banned keywords
        has_banned, keywords = filter_obj.has_banned_headline_keywords("Fake rumor about Chelsea")
        assert has_banned
        assert "fake" in keywords
        assert "rumor" in keywords
        
        # Test empty headline
        has_banned, keywords = filter_obj.has_banned_headline_keywords("")
        assert not has_banned
        assert keywords == []
    
    def test_has_banned_url_keywords(self):
        """Test URL keyword filtering."""
        config = {
            "filter": {
                "banned_url_keywords": ["youtube", "clickbait", "sponsored"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        # Test clean URL
        has_banned, keywords = filter_obj.has_banned_url_keywords("https://bbc.com/news/chelsea-story")
        assert not has_banned
        assert keywords == []
        
        # Test URL with banned keyword
        has_banned, keywords = filter_obj.has_banned_url_keywords("https://youtube.com/watch?v=123")
        assert has_banned
        assert "youtube" in keywords
        
        # Test case insensitive
        has_banned, keywords = filter_obj.has_banned_url_keywords("https://site.com/CLICKBAIT-story")
        assert has_banned
        assert "clickbait" in keywords
    
    def test_filter_story_pass_confirmed_source(self):
        """Test filtering a story that passes (confirmed source)."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor"],
                "banned_url_keywords": ["youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        story = Story(
            story_id="1",
            title="Chelsea wins Premier League",
            url="https://bbc.com/news/chelsea-wins",
            date="2025-06-20",
            source="BBC News"
        )
        
        should_keep, reason, metadata = filter_obj.filter_story(story)
        
        assert should_keep
        assert "Passed all filters" in reason
        assert metadata["source_type"] == "confirmed"
    
    def test_filter_story_pass_accepted_source(self):
        """Test filtering a story that passes (accepted source)."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor"],
                "banned_url_keywords": ["youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        story = Story(
            story_id="2",
            title="Chelsea transfer news",
            url="https://theguardian.com/chelsea-transfer",
            date="2025-06-20",
            source="The Guardian"
        )
        
        should_keep, reason, metadata = filter_obj.filter_story(story)
        
        assert should_keep
        assert "Passed all filters" in reason
        assert metadata["source_type"] == "accepted"
    
    def test_filter_story_fail_source(self):
        """Test filtering a story that fails (banned source)."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor"],
                "banned_url_keywords": ["youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        story = Story(
            story_id="3",
            title="Chelsea news",
            url="https://randomblog.com/chelsea",
            date="2025-06-20",
            source="Random Blog"
        )
        
        should_keep, reason, metadata = filter_obj.filter_story(story)
        
        assert not should_keep
        assert "not in confirmed or accepted sources" in reason
        assert metadata["source_type"] == "banned"
    
    def test_filter_story_fail_headline_keyword(self):
        """Test filtering a story that fails (banned headline keyword)."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor"],
                "banned_url_keywords": ["youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        story = Story(
            story_id="4",
            title="Chelsea transfer rumor emerges",
            url="https://bbc.com/chelsea-rumor",
            date="2025-06-20",
            source="BBC News"
        )
        
        should_keep, reason, metadata = filter_obj.filter_story(story)
        
        assert not should_keep
        assert "banned keywords" in reason
        assert "rumor" in reason
    
    def test_filter_story_fail_url_keyword(self):
        """Test filtering a story that fails (banned URL keyword)."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor"],
                "banned_url_keywords": ["youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        story = Story(
            story_id="5",
            title="Chelsea news",
            url="https://youtube.com/watch?v=chelsea",
            date="2025-06-20",
            source="BBC News"
        )
        
        should_keep, reason, metadata = filter_obj.filter_story(story)
        
        assert not should_keep
        assert "URL contains banned keywords" in reason
        assert "youtube" in reason
    
    def test_filter_stories_multiple(self):
        """Test filtering multiple stories."""
        config = {
            "filter": {
                "confirmed_sources": ["BBC News"],
                "accepted_sources": ["The Guardian"],
                "banned_headline_keywords": ["rumor"],
                "banned_url_keywords": ["youtube"]
            }
        }
        
        filter_obj = StoryFilter(config)
        
        stories = [
            Story(story_id="1", title="Chelsea wins", url="https://bbc.com/1", date="2025-06-20", source="BBC News"),
            Story(story_id="2", title="Chelsea news", url="https://theguardian.com/2", date="2025-06-20", source="The Guardian"),
            Story(story_id="3", title="Chelsea rumor", url="https://bbc.com/3", date="2025-06-20", source="BBC News"),
            Story(story_id="4", title="Chelsea news", url="https://randomblog.com/4", date="2025-06-20", source="Random Blog"),
        ]
        
        filtered_stories, stats = filter_obj.filter_stories(stories)
        
        assert len(filtered_stories) == 2
        assert stats["total"] == 4
        assert stats["passed"] == 2
        assert stats["filtered_out"] == 2
        assert stats["source_types"]["confirmed"] == 1
        assert stats["source_types"]["accepted"] == 1
    
    def test_filter_stories_empty_list(self):
        """Test filtering an empty list of stories."""
        config = {"filter": {}}
        filter_obj = StoryFilter(config)
        
        filtered_stories, stats = filter_obj.filter_stories([])
        
        assert filtered_stories == []
        assert stats["total"] == 0
        assert stats["passed"] == 0
        assert stats["filtered_out"] == 0
