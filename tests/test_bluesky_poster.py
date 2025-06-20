"""Test cases for the BlueSkyPoster class."""

from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from bluesky_poster import BlueSkyPoster
from storage import Story, PostStatus


class TestBlueSkyPoster:
    """Test cases for the BlueSkyPoster class."""
    
    def test_initialization(self):
        """Test BlueSky poster initialization with configuration."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            },
            "rate_limit": {
                "post_interval_minutes": 30
            }
        }
        
        poster = BlueSkyPoster(config)
        
        assert poster.handle == "test.bsky.social"
        assert poster.app_password == "test-password"
        assert poster.post_interval_minutes == 30
        assert poster.client is not None
        assert not poster.authenticated
    
    def test_initialization_empty_config(self):
        """Test BlueSky poster initialization with empty configuration."""
        config = {}
        
        poster = BlueSkyPoster(config)
        
        assert poster.handle == ""
        assert poster.app_password == ""
        assert poster.post_interval_minutes == 30  # default
        assert poster.client is None
    
    @patch('bluesky_poster.Client')
    def test_authenticate_success(self, mock_client_class):
        """Test successful authentication."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            }
        }
        
        # Mock the client instance
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.authenticate.return_value = None  # No exception means success
        
        poster = BlueSkyPoster(config)
        result = poster.authenticate()
        
        assert result is True
        assert poster.authenticated is True
        mock_client.authenticate.assert_called_once_with("test.bsky.social", "test-password")
    
    @patch('bluesky_poster.Client')
    def test_authenticate_failure(self, mock_client_class):
        """Test failed authentication."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "wrong-password"
            }
        }
        
        # Mock the client instance to raise an exception
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.authenticate.side_effect = Exception("Auth failed")
        
        poster = BlueSkyPoster(config)
        result = poster.authenticate()
        
        assert result is False
        assert poster.authenticated is False
    
    def test_authenticate_no_credentials(self):
        """Test authentication with missing credentials."""
        config = {
            "bluesky": {
                "handle": "",
                "app_password": ""
            }
        }
        
        poster = BlueSkyPoster(config)
        result = poster.authenticate()
        
        assert result is False
        assert poster.authenticated is False
    
    def test_can_post_now_no_previous_posts(self):
        """Test rate limiting when there are no previous posts."""
        config = {
            "rate_limit": {
                "post_interval_minutes": 30
            }
        }
        
        poster = BlueSkyPoster(config)
        
        can_post, reason = poster.can_post_now()
        
        assert can_post is True
        assert "No previous posts" in reason
    
    def test_can_post_now_sufficient_time_elapsed(self):
        """Test rate limiting when sufficient time has elapsed."""
        config = {
            "rate_limit": {
                "post_interval_minutes": 30
            }
        }
        
        poster = BlueSkyPoster(config)
        
        # Set last post time to 31 minutes ago
        poster.last_successful_post_time = datetime.now() - timedelta(minutes=31)
        
        can_post, reason = poster.can_post_now()
        
        assert can_post is True
        assert "Sufficient time elapsed" in reason
    
    def test_can_post_now_rate_limited(self):
        """Test rate limiting when not enough time has elapsed."""
        config = {
            "rate_limit": {
                "post_interval_minutes": 30
            }
        }
        
        poster = BlueSkyPoster(config)
        
        # Set last post time to 5 minutes ago
        poster.last_successful_post_time = datetime.now() - timedelta(minutes=5)
        
        can_post, reason = poster.can_post_now()
        
        assert can_post is False
        assert "Rate limit active" in reason
    
    @patch('bluesky_poster.Client')
    def test_post_story_success(self, mock_client_class):
        """Test successful story posting."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            }
        }
        
        # Mock the client
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.authenticate.return_value = None
        mock_client.post.return_value = True
        
        poster = BlueSkyPoster(config)
        poster.authenticated = True  # Skip auth for this test
        
        story = Story(
            story_id="1",
            title="Test News",
            url="https://example.com/1",
            date="2025-06-20",
            source="Test Source",
            summary="This is a test summary for posting."
        )
        
        status, reason = poster.post_story(story)
        
        assert status == PostStatus.posted
        assert "Posted successfully" in reason
        # Check that a Post object was created and passed to the client
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args[0]
        assert len(call_args) >= 1  # At least one argument (the Post object)
    
    @patch('bluesky_poster.Client')
    def test_post_story_failure(self, mock_client_class):
        """Test failed story posting."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            }
        }
        
        # Mock the client to fail posting
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.authenticate.return_value = None
        mock_client.post.side_effect = Exception("Post failed")
        
        poster = BlueSkyPoster(config)
        poster.authenticated = True
        
        story = Story(
            story_id="1",
            title="Test News",
            url="https://example.com/1",
            date="2025-06-20",
            source="Test Source",
            summary="This is a test summary."
        )
        
        status, reason = poster.post_story(story)
        
        assert status == PostStatus.failed
        assert "Post failed" in reason
    
    def test_post_story_no_summary(self):
        """Test posting story with no summary."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            }
        }
        
        poster = BlueSkyPoster(config)
        poster.authenticated = True
        
        story = Story(
            story_id="1",
            title="Test News",
            url="https://example.com/1",
            date="2025-06-20",
            source="Test Source"
            # No summary
        )
        
        status, reason = poster.post_story(story)
        
        assert status == PostStatus.failed
        assert "No summary available" in reason
    
    def test_post_story_too_long(self):
        """Test posting story that exceeds character limit."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            }
        }
        
        with patch('bluesky_poster.Client') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.authenticate.return_value = None
            mock_client.post.return_value = True
            
            poster = BlueSkyPoster(config)
            poster.authenticated = True
            
            # Create a very long summary (over 300 chars)
            long_summary = "A" * 350
            
            story = Story(
                story_id="1",
                title="Test News",
                url="https://example.com/1",
                date="2025-06-20",
                source="Test Source",
                summary=long_summary
            )
            
            status, reason = poster.post_story(story)
            
            assert status == PostStatus.posted
            # Check that a Post object was created and passed to the client
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args[0]
            assert len(call_args) >= 1  # At least one argument (the Post object)
    
    def test_post_story_rate_limited(self):
        """Test posting when rate limited."""
        config = {
            "rate_limit": {
                "post_interval_minutes": 30
            }
        }
        
        poster = BlueSkyPoster(config)
        poster.authenticated = True
        poster.last_successful_post_time = datetime.now() - timedelta(minutes=5)
        
        story = Story(
            story_id="1",
            title="Test News",
            url="https://example.com/1",
            date="2025-06-20",
            source="Test Source",
            summary="Test summary"
        )
        
        status, reason = poster.post_story(story)
        
        assert status == PostStatus.skipped
        assert "Rate limited" in reason
    
    @patch('bluesky_poster.Client')
    def test_post_stories_multiple(self, mock_client_class):
        """Test posting multiple stories with rate limiting."""
        config = {
            "bluesky": {
                "handle": "test.bsky.social",
                "app_password": "test-password"
            },
            "rate_limit": {
                "post_interval_minutes": 30
            }
        }
        
        # Mock successful posting
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.authenticate.return_value = None
        mock_client.post.return_value = True
        
        poster = BlueSkyPoster(config)
        poster.authenticated = True
        
        stories = [
            Story(story_id="1", title="News 1", url="https://example.com/1", 
                  date="2025-06-20", source="Source 1", summary="Summary 1"),
            Story(story_id="2", title="News 2", url="https://example.com/2", 
                  date="2025-06-20", source="Source 2", summary="Summary 2"),
            Story(story_id="3", title="News 3", url="https://example.com/3", 
                  date="2025-06-20", source="Source 3", summary="Summary 3"),
        ]
        
        stats = poster.post_stories(stories)
        
        # Should only post one story due to rate limiting
        assert stats["total"] == 3
        assert stats["posted"] == 1
        assert stats["failed"] == 0
        assert stats["skipped"] == 0
        assert stats["rate_limited"] == 0
        
        # Check that only the first story was posted
        assert stories[0].post_status == PostStatus.posted
        assert stories[1].post_status is None  # Not processed
        assert stories[2].post_status is None  # Not processed
    
    def test_post_stories_skip_already_posted(self):
        """Test that already posted stories are skipped."""
        config = {}
        
        poster = BlueSkyPoster(config)
        
        stories = [
            Story(story_id="1", title="News 1", url="https://example.com/1", 
                  date="2025-06-20", source="Source 1", summary="Summary 1",
                  post_status=PostStatus.posted),  # Already posted
            Story(story_id="2", title="News 2", url="https://example.com/2", 
                  date="2025-06-20", source="Source 2", summary="Summary 2"),
        ]
        
        stats = poster.post_stories(stories)
        
        assert stats["total"] == 2
        assert stats["posted"] == 0
        assert stats["skipped"] == 1
    
    def test_set_last_post_time(self):
        """Test setting the last successful post time."""
        config = {}
        
        poster = BlueSkyPoster(config)
        
        test_time = datetime.now() - timedelta(hours=1)
        poster.set_last_post_time(test_time)
        
        assert poster.last_successful_post_time == test_time
