"""
Tests for the summarizer module.
"""

from unittest.mock import Mock, patch

from summarizer import Summarizer
from storage import Story


class TestSummarizer:

    def setup_method(self):
        """Set up test fixtures."""
        self.config = {"api_key": "test-api-key", "max_length": 300, "retry_count": 2, "model": "gpt-3.5-turbo"}

    def test_initialization_with_openai(self):
        """Test summarizer initialization with OpenAI available."""
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_client = Mock()
            mock_openai_class.return_value = mock_client

            # Mock successful models list call
            mock_model = Mock()
            mock_model.id = "gpt-3.5-turbo"
            mock_models_response = Mock()
            mock_models_response.data = [mock_model]
            mock_client.models.list.return_value = mock_models_response

            summarizer = Summarizer(self.config)

            assert summarizer.openai_enabled is True
            assert summarizer.client == mock_client
            assert summarizer.max_length == 300
            assert summarizer.retry_count == 2
            assert summarizer.model == "gpt-3.5-turbo"
            mock_openai_class.assert_called_once_with(api_key="test-api-key")

    def test_initialization_without_openai(self):
        """Test summarizer initialization without OpenAI available."""
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")

            summarizer = Summarizer(self.config)

            assert summarizer.openai_enabled is False
            assert summarizer.client is None

    def test_initialization_without_api_key(self):
        """Test summarizer initialization without API key."""
        config_no_key = {**self.config}
        del config_no_key["api_key"]

        summarizer = Summarizer(config_no_key)

        assert summarizer.openai_enabled is False
        assert summarizer.client is None

    def test_is_video_content(self):
        """Test video content detection."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer(self.config)

            # Video URLs
            assert summarizer._is_video_content("https://youtube.com/watch?v=123") is True
            assert summarizer._is_video_content("https://example.com/video/news") is True
            assert summarizer._is_video_content("https://vimeo.com/123456") is True
            assert summarizer._is_video_content("https://example.com/player/embed") is True

            # Non-video URLs
            assert summarizer._is_video_content("https://example.com/article") is False
            assert summarizer._is_video_content("https://news.com/story") is False
            assert summarizer._is_video_content("") is False

    def test_summarize_story_video_content(self):
        """Test summarization for video content."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer(self.config)

            story = Story(
                story_id="test_video",
                title="Breaking News Video",
                url="https://youtube.com/watch?v=123",
                date="2025-01-15",
                source="Test Source",
                byline="Test Reporter",
            )

            summary, used_condensation = summarizer.summarize_story(story)

            expected = "Video: Breaking News Video By Test Reporter. [Test Source](https://youtube.com/watch?v=123)"
            assert summary == expected
            assert used_condensation is False

    def test_summarize_story_no_full_text(self):
        """Test summarization when no full text is available."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer(self.config)

            story = Story(
                story_id="test_no_text",
                title="Breaking News",
                url="https://example.com/news",
                date="2025-01-15",
                source="Test Source",
                full_text="",
            )

            summary, used_condensation = summarizer.summarize_story(story)

            expected = "Breaking News [Test Source](https://example.com/news)"
            assert summary == expected
            assert used_condensation is False

    def test_summarize_story_with_byline(self):
        """Test summarization includes byline correctly."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer(self.config)

            story = Story(
                story_id="test_byline",
                title="Breaking News",
                url="https://example.com/news",
                date="2025-01-15",
                source="Test Source",
                byline="John Doe",
            )

            summary, used_condensation = summarizer.summarize_story(story)

            expected = "Breaking News By John Doe. [Test Source](https://example.com/news)"
            assert summary == expected
            assert used_condensation is False

    def test_summarize_story_with_decoded_url(self):
        """Test summarization uses decoded URL for source link."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer(self.config)

            story = Story(
                story_id="test_decoded",
                title="Breaking News",
                url="https://google.com/redirect",
                decoded_url="https://example.com/real-article",
                date="2025-01-15",
                source="Test Source",
            )

            summary, used_condensation = summarizer.summarize_story(story)

            expected = "Breaking News [Test Source](https://example.com/real-article)"
            assert summary == expected
            assert used_condensation is False

    @patch("summarizer.OpenAI")
    def test_summarize_story_with_openai_success(self, mock_openai_class):
        """Test successful OpenAI summarization."""
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Mock successful models list call
        mock_model = Mock()
        mock_model.id = "gpt-3.5-turbo"
        mock_models_response = Mock()
        mock_models_response.data = [mock_model]
        mock_client.models.list.return_value = mock_models_response

        # Mock response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "This is a concise AI-generated summary of the news article."
        mock_response.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response

        summarizer = Summarizer(self.config)

        story = Story(
            story_id="test_openai",
            title="Long News Article Title",
            url="https://example.com/news",
            date="2025-01-15",
            source="Test Source",
            full_text="This is a very long article with lots of content that needs to be summarized by AI. " * 10,
        )

        summary, used_condensation = summarizer.summarize_story(story)

        expected = "This is a concise AI-generated summary of the news article. [Test Source](https://example.com/news)"
        assert summary == expected
        assert used_condensation is False  # First successful attempt should not use condensation

        # Verify OpenAI was called
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert len(call_args[1]["messages"]) == 2
        assert "system" in call_args[1]["messages"][0]["role"]
        assert "user" in call_args[1]["messages"][1]["role"]

    @patch("summarizer.OpenAI")
    def test_summarize_story_openai_failure_fallback(self, mock_openai_class):
        """Test fallback to headline when OpenAI fails."""
        # Setup mock OpenAI client that fails
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Mock successful models list call first
        mock_model = Mock()
        mock_model.id = "gpt-3.5-turbo"
        mock_models_response = Mock()
        mock_models_response.data = [mock_model]
        mock_client.models.list.return_value = mock_models_response

        # But then make the chat completion fail
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        summarizer = Summarizer(self.config)

        story = Story(
            story_id="test_openai_fail",
            title="News Article",
            url="https://example.com/news",
            date="2025-01-15",
            source="Test Source",
            full_text="This is a long article that should be summarized but will fail.",
        )

        summary, used_condensation = summarizer.summarize_story(story)

        # Should fallback to headline
        expected = "News Article [Test Source](https://example.com/news)"
        assert summary == expected
        assert used_condensation is False

    def test_format_final_summary_length_compliance(self):
        """Test that final summary respects length limits."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer({"max_length": 100})  # Very short limit

            story = Story(
                story_id="test_length",
                title="This is a very long title that would exceed the character limit when combined with byline and source",
                url="https://example.com/very-long-url-that-adds-more-characters",
                date="2025-01-15",
                source="Very Long Source Name",
                byline="Very Long Reporter Name",
            )

            # Test with a long summary
            long_summary = "This is a very long summary that would definitely exceed the character limit."
            final_summary = summarizer._format_final_summary(long_summary, story)

            # Calculate counted characters (per PRD: summary + byline + source name, not URL)
            import re

            markdown_link_pattern = r"\[([^\]]+)\]\([^)]+\)$"
            match = re.search(markdown_link_pattern, final_summary)
            if match:
                source_name = match.group(1)
                url_start = match.start()
                summary_without_url = final_summary[:url_start] + f"[{source_name}]"
                counted_chars = len(summary_without_url)
            else:
                counted_chars = len(final_summary)

            assert counted_chars <= 100
            assert "Very Long Source Name" in final_summary
            assert "Very Long Reporter Name" in final_summary

    def test_summarize_stories_batch(self):
        """Test batch summarization of multiple stories."""
        # Mock OpenAI to fail so we can test without it
        with patch("summarizer.OpenAI") as mock_openai_class:
            mock_openai_class.side_effect = KeyError("API key not found")
            summarizer = Summarizer(self.config)

            stories = [
                Story(
                    story_id="story1", title="News 1", url="https://example.com/1", date="2025-01-15", source="Source 1"
                ),
                Story(
                    story_id="story2",
                    title="Video News",
                    url="https://youtube.com/watch?v=123",
                    date="2025-01-15",
                    source="Source 2",
                ),
                Story(
                    story_id="story3",
                    title="News 3",
                    url="https://example.com/3",
                    date="2025-01-15",
                    source="Source 3",
                    summary="Already has summary",  # Should be skipped
                ),
            ]

            updated_stories, stats = summarizer.summarize_stories(stories)

            assert len(updated_stories) == 3
            assert stats["total_stories"] == 3
            assert stats["summarized"] == 2  # One already had summary
            assert stats["used_headline"] == 1
            assert stats["used_video_prefix"] == 1
            assert stats["used_openai"] == 0  # OpenAI not available
            assert stats["failed"] == 0

            # Check that summaries were generated
            assert updated_stories[0].summary is not None
            assert updated_stories[1].summary is not None
            assert "Video:" in updated_stories[1].summary
            assert updated_stories[2].summary == "Already has summary"  # Unchanged
