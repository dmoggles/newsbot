from deduplicator import StoryDeduplicator
from storage import Story

class TestStoryDeduplicator:
    
    def test_initialization(self):
        """Test that deduplicator initializes correctly."""
        deduplicator = StoryDeduplicator()
        assert len(deduplicator.url_hashes) == 0
        assert len(deduplicator.headline_hashes) == 0
        assert len(deduplicator.existing_story_ids) == 0
    
    def test_normalize_url(self):
        """Test URL normalization removes tracking parameters."""
        deduplicator = StoryDeduplicator()
        
        # Test removing UTM parameters
        url_with_utm = "https://example.com/article?utm_source=google&utm_medium=cpc&id=123"
        normalized = deduplicator._normalize_url(url_with_utm)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "id=123" in normalized
        
        # Test removing Facebook click ID
        url_with_fbclid = "https://example.com/article?fbclid=abc123&id=456"
        normalized = deduplicator._normalize_url(url_with_fbclid)
        assert "fbclid" not in normalized
        assert "id=456" in normalized
        
        # Test case insensitive
        url_mixed_case = "https://Example.COM/Article"
        normalized = deduplicator._normalize_url(url_mixed_case)
        assert normalized == "https://example.com/article"
    
    def test_normalize_headline(self):
        """Test headline normalization."""
        deduplicator = StoryDeduplicator()
        
        # Test whitespace normalization
        headline_with_spaces = "  Chelsea   FC   wins   match  "
        normalized = deduplicator._normalize_headline(headline_with_spaces)
        assert normalized == "chelsea fc wins match"
        
        # Test punctuation removal
        headline_with_punct = 'Chelsea FC "wins" match!'
        normalized = deduplicator._normalize_headline(headline_with_punct)
        assert normalized == "chelsea fc wins match"
        
        # Test trailing punctuation
        headline_trailing = "Chelsea FC wins match..."
        normalized = deduplicator._normalize_headline(headline_trailing)
        assert normalized == "chelsea fc wins match"
    
    def test_is_google_news_redirect(self):
        """Test Google News redirect detection."""
        deduplicator = StoryDeduplicator()
        
        google_url = "https://news.google.com/articles/CBMiXWh0dHBzOi8vd3d3LmJiYy5jb20vc3BvcnQvZm9vdGJhbGwvMTIzNDU2NzjSAQA"
        if deduplicator._is_google_news_redirect(google_url):
            assert True
        else:
            assert False
        
        normal_url = "https://www.bbc.com/sport/football/12345678"
        if not deduplicator._is_google_news_redirect(normal_url):
            assert True
        else:
            assert False
    
    def test_load_existing_stories(self):
        """Test loading existing stories for deduplication."""
        deduplicator = StoryDeduplicator()
        
        existing_stories = [
            Story(
                story_id="story1",
                title="Chelsea FC wins match",
                url="https://example.com/article1",
                date="2025-06-20",
                source="BBC Sport"
            ),
            Story(
                story_id="story2", 
                title="Arsenal loses game",
                url="https://example.com/article2",
                date="2025-06-20",
                source="Sky Sports"
            )
        ]
        
        deduplicator.load_existing_stories(existing_stories)
        
        assert len(deduplicator.existing_story_ids) == 2
        assert "story1" in deduplicator.existing_story_ids
        assert "story2" in deduplicator.existing_story_ids
        assert len(deduplicator.url_hashes) == 2
        assert len(deduplicator.headline_hashes) == 2
    
    def test_deduplicate_by_story_id(self):
        """Test deduplication by story ID."""
        deduplicator = StoryDeduplicator()
        
        # Load existing story
        existing_stories = [
            Story(
                story_id="existing_story",
                title="Existing story",
                url="https://example.com/existing",
                date="2025-06-20",
                source="Source A"
            )
        ]
        deduplicator.load_existing_stories(existing_stories)
        
        # Try to add duplicate story ID
        new_stories = [
            Story(
                story_id="existing_story",  # Same ID
                title="Different title",
                url="https://example.com/different",
                date="2025-06-20",
                source="Source B"
            ),
            Story(
                story_id="new_story",
                title="New story",
                url="https://example.com/new",
                date="2025-06-20",
                source="Source C"
            )
        ]
        
        unique_stories, stats = deduplicator.deduplicate_stories(new_stories)
        
        assert len(unique_stories) == 1
        assert unique_stories[0].story_id == "new_story"
        assert stats['duplicates_by_story_id'] == 1
        assert stats['unique_output'] == 1
    
    def test_deduplicate_by_url(self):
        """Test deduplication by URL."""
        deduplicator = StoryDeduplicator()
        
        # Load existing story
        existing_stories = [
            Story(
                story_id="existing_story",
                title="Existing story",
                url="https://example.com/article?id=123",
                date="2025-06-20",
                source="Source A"
            )
        ]
        deduplicator.load_existing_stories(existing_stories)
        
        # Try to add story with same URL (but different tracking params)
        new_stories = [
            Story(
                story_id="new_story_1",
                title="Different title",
                url="https://example.com/article?id=123&utm_source=google",  # Same base URL
                date="2025-06-20",
                source="Source B"
            ),
            Story(
                story_id="new_story_2",
                title="Unique story",
                url="https://example.com/different-article",
                date="2025-06-20",
                source="Source C"
            )
        ]
        
        unique_stories, stats = deduplicator.deduplicate_stories(new_stories)
        
        assert len(unique_stories) == 1
        assert unique_stories[0].story_id == "new_story_2"
        assert stats['duplicates_by_url'] == 1
        assert stats['unique_output'] == 1
    
    def test_deduplicate_by_headline(self):
        """Test deduplication by headline."""
        deduplicator = StoryDeduplicator()
        
        # Load existing story
        existing_stories = [
            Story(
                story_id="existing_story",
                title="Chelsea FC wins match",
                url="https://example.com/article1",
                date="2025-06-20",
                source="Source A"
            )
        ]
        deduplicator.load_existing_stories(existing_stories)
        
        # Try to add story with similar headline
        new_stories = [
            Story(
                story_id="new_story_1",
                title="Chelsea FC wins match!",  # Similar headline (with punctuation)
                url="https://example.com/article2",
                date="2025-06-20",
                source="Source B"
            ),
            Story(
                story_id="new_story_2",
                title="Arsenal loses game",
                url="https://example.com/article3",
                date="2025-06-20",
                source="Source C"
            )
        ]
        
        unique_stories, stats = deduplicator.deduplicate_stories(new_stories)
        
        assert len(unique_stories) == 1
        assert unique_stories[0].story_id == "new_story_2"
        assert stats['duplicates_by_headline'] == 1
        assert stats['unique_output'] == 1
    
    def test_skip_google_news_urls_for_deduplication(self):
        """Test that Google News redirect URLs are skipped for URL-based deduplication."""
        deduplicator = StoryDeduplicator()
        
        # Both stories have Google News URLs - should not be deduplicated by URL
        new_stories = [
            Story(
                story_id="story1",
                title="Different title 1",
                url="https://news.google.com/articles/CBMiXWh0dHBzOi8vd3d3LmJiYy5jb20vc3BvcnQvZm9vdGJhbGwvMTIzNDU2NzjSAQA",
                date="2025-06-20",
                source="BBC Sport"
            ),
            Story(
                story_id="story2",
                title="Different title 2", 
                url="https://news.google.com/articles/CBMiXWh0dHBzOi8vd3d3LnNreXNwb3J0cy5jb20vZm9vdGJhbGwvOTg3NjU0MzLSAQA",
                date="2025-06-20",
                source="Sky Sports"
            )
        ]
        
        unique_stories, stats = deduplicator.deduplicate_stories(new_stories)
        
        # Both should remain since Google News URLs are skipped for URL deduplication
        assert len(unique_stories) == 2
        assert stats['duplicates_by_url'] == 0
        assert stats['unique_output'] == 2
    
    def test_batch_deduplication(self):
        """Test deduplication within the same batch."""
        deduplicator = StoryDeduplicator()
        
        # No existing stories
        deduplicator.load_existing_stories([])
        
        # Stories with duplicates within the same batch
        new_stories = [
            Story(
                story_id="story1",
                title="Chelsea FC wins",
                url="https://example.com/article1",
                date="2025-06-20",
                source="Source A"
            ),
            Story(
                story_id="story2",
                title="Chelsea FC wins!",  # Similar headline
                url="https://example.com/article2", 
                date="2025-06-20",
                source="Source B"
            ),
            Story(
                story_id="story3",
                title="Different story",
                url="https://example.com/article1?utm_source=google",  # Similar URL
                date="2025-06-20",
                source="Source C"
            ),
            Story(
                story_id="story4",
                title="Unique story",
                url="https://example.com/unique",
                date="2025-06-20",
                source="Source D"
            )
        ]
        
        unique_stories, stats = deduplicator.deduplicate_stories(new_stories)
        
        # Should keep story1 and story4 (first unique headline and URL, plus unique story)
        assert len(unique_stories) == 2
        assert stats['duplicates_by_headline'] == 1
        assert stats['duplicates_by_url'] == 1
        assert stats['unique_output'] == 2
    
    def test_semantic_deduplication_placeholder(self):
        """Test that semantic deduplication placeholders work correctly."""
        deduplicator = StoryDeduplicator()
        
        # Create two stories that might be semantically similar
        story1 = Story(
            story_id="story1",
            title="Chelsea FC wins championship",
            url="https://example.com/article1",
            date="2025-06-20",
            source="BBC Sport"
        )
        story2 = Story(
            story_id="story2", 
            title="Chelsea claims title victory",  # Semantically similar but different words
            url="https://example.com/article2",
            date="2025-06-20",
            source="Sky Sports"
        )
        
        # Test semantic similarity calculation (placeholder)
        similarity = deduplicator._calculate_semantic_similarity(story1, story2)
        assert similarity == 0.0  # Placeholder always returns 0.0
        
        # Test semantic duplicate detection (placeholder)
        is_duplicate, reason = deduplicator._is_semantically_duplicate(story1, [story2])
        if not is_duplicate:
            assert reason == "semantic_deduplication_not_implemented"
        else:
            assert False, "Expected semantic deduplication to not be implemented"
        
    
    def test_semantic_deduplication_integration(self):
        """Test that semantic deduplication can be enabled but doesn't affect results yet."""
        deduplicator = StoryDeduplicator()
        
        # No existing stories
        deduplicator.load_existing_stories([])
        
        # Stories that might be semantically similar
        stories = [
            Story(
                story_id="story1",
                title="Chelsea FC wins championship",
                url="https://example.com/article1",
                date="2025-06-20",
                source="BBC Sport"
            ),
            Story(
                story_id="story2",
                title="Chelsea claims title victory",  # Semantically similar
                url="https://example.com/article2", 
                date="2025-06-20",
                source="Sky Sports"
            )
        ]
        
        # Test with semantic deduplication disabled (default)
        unique_stories, stats = deduplicator.deduplicate_stories(stories, enable_semantic=False)
        assert len(unique_stories) == 2  # Both stories should remain
        assert stats['duplicates_by_semantic'] == 0
        
        # Test with semantic deduplication enabled (placeholder)
        unique_stories, stats = deduplicator.deduplicate_stories(stories, enable_semantic=True)
        assert len(unique_stories) == 2  # Both stories should still remain (placeholder doesn't remove any)
        assert stats['duplicates_by_semantic'] == 0  # Placeholder doesn't detect semantic duplicates
