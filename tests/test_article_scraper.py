from unittest.mock import Mock, patch
from datetime import datetime

from article_scraper import ArticleScraper
from storage import Story, PostStatus, ScrapingStatus


class TestArticleScraper:
    """Test cases for ArticleScraper."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.scraper = ArticleScraper(timeout=10, max_retries=2, delay_between_requests=0.1)
        
        # Sample story for testing
        self.sample_story = Story(
            story_id="test_story_1",
            title="Test Article Title",
            url="https://example.com/article",
            date="2025-01-15",
            source="Test Source",
            byline="Test Author",
            post_status=PostStatus.pending,
            filter_status="passed",
            filter_reason="confirmed source"
        )
    
    def test_normalize_text(self):
        """Test text normalization functionality."""
        # Test basic normalization
        text = "  This is a test   with   extra    spaces  "
        normalized = self.scraper._normalize_text(text)
        assert normalized == "This is a test with extra spaces"
        
        # Test Unicode normalization
        text_with_unicode = "Café naïve résumé"
        normalized = self.scraper._normalize_text(text_with_unicode)
        # Should normalize Unicode characters
        assert normalized == "Cafe naive resume"
        
        # Test with non-printable characters
        text_with_control = "Normal text\x00\x01\x02with control chars"
        normalized = self.scraper._normalize_text(text_with_control)
        assert "\x00" not in normalized
        assert "\x01" not in normalized
        assert "\x02" not in normalized
    
    @patch('article_scraper.LANGDETECT_AVAILABLE', True)
    @patch('article_scraper.detect')
    def test_detect_language(self, mock_detect):
        """Test language detection."""
        # Test successful detection
        mock_detect.return_value = 'en'
        
        text = "This is an English text that should be detected as English."
        result = self.scraper._detect_language(text)
        
        assert result == 'en'
        mock_detect.assert_called_once()
        
        # Test failed detection
        mock_detect.side_effect = Exception("Detection failed")
        result = self.scraper._detect_language(text)
        assert result is None
    
    @patch('article_scraper.LANGDETECT_AVAILABLE', False)
    def test_detect_language_unavailable(self):
        """Test language detection when library is not available."""
        text = "This is an English text."
        result = self.scraper._detect_language(text)
        assert result is None
    
    def test_needs_translation(self):
        """Test translation needs assessment."""
        with patch.object(self.scraper, '_detect_language') as mock_detect:
            # Test English text (no translation needed)
            mock_detect.return_value = 'en'
            assert not self.scraper._needs_translation("English text")
            
            # Test Spanish text (translation needed)
            mock_detect.return_value = 'es'
            assert self.scraper._needs_translation("Texto en español")
            
            # Test unknown language (no translation)
            mock_detect.return_value = None
            assert not self.scraper._needs_translation("Unknown text")
    
    @patch('article_scraper.requests.get')
    def test_fetch_html_success(self, mock_get):
        """Test successful HTML fetching."""
        mock_response = Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.scraper._fetch_html("https://example.com")
        
        assert result == "<html><body>Test content</body></html>"
        mock_get.assert_called_once()
    
    @patch('article_scraper.requests.get')
    def test_fetch_html_failure(self, mock_get):
        """Test HTML fetching with failures and retries."""
        mock_get.side_effect = Exception("Connection failed")
        
        result = self.scraper._fetch_html("https://example.com")
        
        assert result is None
        assert mock_get.call_count == self.scraper.max_retries
    
    @patch('article_scraper.NEWSPAPER_AVAILABLE', True)
    @patch('article_scraper.Article')
    def test_scrape_with_newspaper(self, mock_article_class):
        """Test scraping with newspaper3k."""
        # Setup mock article
        mock_article = Mock()
        mock_article.title = "Test Article Title"
        mock_article.text = "This is the article content that is long enough to pass validation." * 10
        mock_article.authors = ["Test Author"]
        mock_article.publish_date = datetime(2025, 1, 15)
        mock_article.top_image = "https://example.com/image.jpg"
        mock_article.meta_description = "Test description"
        mock_article.meta_keywords = ["test", "article"]
        
        mock_article_class.return_value = mock_article
        
        html = "<html><body>Test content</body></html>"
        result = self.scraper._scrape_with_newspaper("https://example.com", html)
        
        assert result is not None
        assert result['title'] == "Test Article Title"
        assert result['scraper'].startswith('newspaper3k')
        assert len(result['text']) > 50  # Mock text is ~67 chars
        
        mock_article.set_html.assert_called_once_with(html)
        mock_article.parse.assert_called_once()
    
    @patch('article_scraper.TRAFILATURA_AVAILABLE', True)
    @patch('article_scraper.trafilatura')
    def test_scrape_with_trafilatura(self, mock_trafilatura):
        """Test scraping with trafilatura."""
        # Setup mock
        mock_trafilatura.extract.return_value = "This is extracted content that is long enough to pass validation checks."*10
        
        mock_metadata = Mock()
        mock_metadata.title = "Test Title"
        mock_metadata.author = "Test Author"
        mock_metadata.date = "2025-01-15"
        mock_metadata.description = "Test description"
        
        mock_trafilatura.extract_metadata.return_value = mock_metadata
        
        html = "<html><body>Test content</body></html>"
        result = self.scraper._scrape_with_trafilatura("https://example.com", html)
        
        assert result is not None
        assert result['title'] == "Test Title"
        assert result['scraper'].startswith('trafilatura')
        assert len(result['text']) > 50  # Mock text is ~72 chars
    
    @patch('article_scraper.BS4_AVAILABLE', True)
    def test_scrape_with_beautifulsoup(self):
        """Test scraping with BeautifulSoup."""
        a_very_long_text = "This is a long text that should be sufficient for validation checks." * 10
        html = f"""
        <html>
        <head><title>Test Article Title</title></head>
        <body>
            <article>
                <p>This is the first paragraph of the article content.</p>
                <p>This is the second paragraph with more content to make it long enough.</p>
                <p>And this is the third paragraph to ensure we have sufficient content.</p>
                <p>{a_very_long_text}</p>
            </article>
        </body>
        </html>
        """
        
        result = self.scraper._scrape_with_beautifulsoup("https://example.com", html)
        
        assert result is not None
        assert result['title'] == "Test Article Title"
        assert result['scraper'] == 'beautifulsoup4'
        assert len(result['text']) > 100
        assert "first paragraph" in result['text']
        assert "second paragraph" in result['text']
    
    def test_scrape_basic_fallback(self):
        """Test basic fallback scraping."""
        html = """
        <html>
        <head><title>Basic Test Title</title></head>
        <body>
            <script>console.log('this should be removed');</script>
            <style>body { color: red; }</style>
            <p>This is the main content of the page that should be extracted.</p>
            <p>More content to ensure we have enough text for the basic scraper.</p>
            <p>Even more content to meet the minimum length requirements for validation.</p>
        </body>
        </html>
        """
        
        result = self.scraper._scrape_basic_fallback("https://example.com", html)
        
        assert result is not None
        assert result['title'] == "Basic Test Title"
        assert result['scraper'] == 'basic_fallback'
        assert "This is the main content" in result['text']
        assert "console.log" not in result['text']  # Script should be removed
        assert "color: red" not in result['text']   # Style should be removed
    
    @patch.object(ArticleScraper, '_fetch_html')
    @patch.object(ArticleScraper, '_scrape_with_newspaper')
    def test_scrape_article_success(self, mock_newspaper, mock_fetch):
        """Test successful article scraping."""
        mock_fetch.return_value = "<html><body>Test content</body></html>"
        mock_newspaper.return_value = {
            'title': 'Test Title',
            'text': 'This is test content that is long enough for validation.',
            'authors': ['Test Author'],
            'scraper': 'newspaper3k'
        }
        
        result = self.scraper.scrape_article("https://example.com/article")
        
        assert result is not None
        assert result['title'] == 'Test Title'
        assert 'scraped_at' in result
        assert 'url' in result
        assert 'content_length' in result
        assert 'detected_language' in result
        assert 'needs_translation' in result
    
    @patch.object(ArticleScraper, '_fetch_html')
    def test_scrape_article_failure(self, mock_fetch):
        """Test article scraping failure."""
        mock_fetch.return_value = None  # Simulate fetch failure
        
        result = self.scraper.scrape_article("https://example.com/article")
        
        assert result is not None
        assert 'errors' in result
        assert 'html_fetch' in result['errors']
        assert result['errors']['html_fetch'] == 'Failed to fetch HTML from URL'
    
    def test_scrape_article_invalid_url(self):
        """Test scraping with invalid URL."""
        result = self.scraper.scrape_article("not-a-valid-url")
        assert result is not None
        assert 'errors' in result
        assert 'url_validation' in result['errors']
        
        result = self.scraper.scrape_article("")
        assert result is not None
        assert 'errors' in result
        assert 'url_validation' in result['errors']
    
    @patch.object(ArticleScraper, 'scrape_article')
    def test_scrape_stories(self, mock_scrape):
        """Test scraping multiple stories."""
        # Setup stories
        stories = [
            Story(
                story_id=f"story_{i}",
                title=f"Story {i}",
                url=f"https://example.com/story{i}",
                date="2025-01-15",
                source="Test Source",
                post_status=PostStatus.pending,
                filter_status="passed"
            ) for i in range(3)
        ]
        
        # Mock scraping results
        mock_scrape.side_effect = [
            {'text': f'Content for story {i}', 'title': f'Story {i}', 'authors': [], 'scraper': 'test'}
            for i in range(3)
        ]
        
        updated_stories, stats = self.scraper.scrape_stories(stories)
        
        assert len(updated_stories) == 3
        assert stats['successfully_scraped'] == 3
        assert stats['scraping_failures'] == 0
        assert stats['already_scraped'] == 0
        assert mock_scrape.call_count == 3
        
        # Check that stories were updated with scraped content and status
        for i, story in enumerate(updated_stories):
            assert story.full_text == f'Content for story {i}'
            assert story.scraping_status == "success"
            assert story.scraping_error is None
            assert story.scraper_used == "test"
    
    @patch.object(ArticleScraper, 'scrape_article')
    def test_scrape_stories_already_scraped(self, mock_scrape):
        """Test skipping stories that already have content."""
        story = Story(
            story_id="story_1",
            title="Story 1",
            url="https://example.com/story1",
            date="2025-01-15",
            source="Test Source",
            full_text="This story already has content that is long enough to skip scraping.",
            post_status=PostStatus.pending,
            filter_status="passed"
        )
        
        updated_stories, stats = self.scraper.scrape_stories([story])
        
        assert len(updated_stories) == 1
        assert stats['successfully_scraped'] == 0
        assert stats['already_scraped'] == 1
        assert mock_scrape.call_count == 0  # Should not call scrape_article
        
        # Check scraping status for already scraped story
        story = updated_stories[0]
        assert story.scraping_status == "skipped"
        assert story.scraping_error is None
    
    @patch.object(ArticleScraper, 'scrape_article')
    def test_scrape_stories_mixed_results(self, mock_scrape):
        """Test scraping with mixed success/failure results."""
        stories = [
            Story(
                story_id="story_1",
                title="Story 1",
                url="https://example.com/story1",
                date="2025-01-15",
                source="Test Source",
                post_status=PostStatus.pending,
                filter_status="passed"
            ),
            Story(
                story_id="story_2", 
                title="Story 2",
                url="https://example.com/story2",
                date="2025-01-15",
                source="Test Source",
                post_status=PostStatus.pending,
                filter_status="passed"
            )
        ]
        
        # First scrape succeeds, second fails
        mock_scrape.side_effect = [
            {'text': 'Content for story 1', 'title': 'Story 1', 'authors': [], 'scraper': 'test'},
            {'errors': {'general': 'All scraping methods failed to extract content'}}  # Failure with error dict
        ]
        
        updated_stories, stats = self.scraper.scrape_stories(stories)
        
        assert len(updated_stories) == 2
        assert stats['successfully_scraped'] == 1
        assert stats['scraping_failures'] == 1
        assert stats['already_scraped'] == 0
        
        # First story should have content and success status, second should have failure status
        assert updated_stories[0].full_text == 'Content for story 1'
        assert updated_stories[0].scraping_status == ScrapingStatus.success
        assert updated_stories[0].scraping_error is None
        assert updated_stories[0].scraper_used == "test"
        
        assert updated_stories[1].full_text is None
        assert updated_stories[1].scraping_status == ScrapingStatus.failed
        assert updated_stories[1].scraping_error == {'general': 'All scraping methods failed to extract content'}
        assert updated_stories[1].scraper_used is None
