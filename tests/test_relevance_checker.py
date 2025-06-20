"""Test cases for the RelevanceChecker class."""

from relevance_checker import RelevanceChecker
from storage import Story, RelevanceStatus


class TestRelevanceChecker:
    """Test cases for the RelevanceChecker class."""
    
    def test_initialization(self):
        """Test relevance checker initialization with configuration."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea", "football"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        assert checker.keywords == ["chelsea", "football"]
        assert checker.strategy == "substring"
    
    def test_initialization_empty_config(self):
        """Test relevance checker initialization with empty configuration."""
        config = {}
        
        checker = RelevanceChecker(config)
        
        assert checker.keywords == []
        assert checker.strategy == "substring"
    
    def test_confirmed_source_skips_check(self):
        """Test that confirmed sources skip relevance checks."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="1",
            title="Random sports news",
            url="https://example.com/1",
            date="2025-06-20",
            source="BBC News",
            summary="This is about basketball, not football"
        )
        
        is_relevant, reason = checker.is_relevant(story, "confirmed")
        
        assert is_relevant is True
        assert "Confirmed source" in reason
    
    def test_no_keywords_configured(self):
        """Test behavior when no keywords are configured."""
        config = {
            "relevance_checker": {
                "keywords": [],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="2",
            title="Random news",
            url="https://example.com/2",
            date="2025-06-20",
            source="The Guardian",
            summary="This is about something completely different"
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        assert is_relevant is True
        assert "No relevance keywords configured" in reason
    
    def test_relevant_story_summary_match(self):
        """Test story that is relevant based on summary keyword match."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea", "football"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="3",
            title="Sports News",
            url="https://example.com/3",
            date="2025-06-20",
            source="The Guardian",
            summary="Chelsea FC won their match yesterday in a thrilling football game"
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        assert is_relevant is True
        assert "Matched relevance keywords" in reason
        assert "chelsea" in reason
        assert "football" in reason
    
    def test_relevant_story_title_match(self):
        """Test story that is relevant based on title keyword match (no summary)."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="4",
            title="Chelsea FC announces new signing",
            url="https://example.com/4",
            date="2025-06-20",
            source="The Guardian"
            # No summary - should fall back to title
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        assert is_relevant is True
        assert "Matched relevance keywords" in reason
        assert "chelsea" in reason
    
    def test_not_relevant_story(self):
        """Test story that is not relevant."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea", "football"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="5",
            title="Basketball News",
            url="https://example.com/5",
            date="2025-06-20",
            source="The Guardian",
            summary="Lakers beat Warriors in basketball game last night"
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        assert is_relevant is False
        assert "No relevance keywords found" in reason
    
    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        config = {
            "relevance_checker": {
                "keywords": ["chelsea"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="6",
            title="CHELSEA FC NEWS",
            url="https://example.com/6",
            date="2025-06-20",
            source="The Guardian",
            summary="CHELSEA scored a goal"
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        assert is_relevant is True
        assert "chelsea" in reason
    
    def test_no_text_available(self):
        """Test story with no summary or title."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="7",
            title="",  # Empty title
            url="https://example.com/7",
            date="2025-06-20",
            source="The Guardian"
            # No summary
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        assert is_relevant is False
        assert "No text available for relevance checking" in reason
    
    def test_check_stories_multiple(self):
        """Test checking multiple stories with different relevance outcomes."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea"],
                "strategy": "substring"
            }
        }
        
        checker = RelevanceChecker(config)
        
        stories = [
            Story(story_id="1", title="Chelsea FC news", url="https://example.com/1", 
                  date="2025-06-20", source="BBC News", summary="Chelsea won"),
            Story(story_id="2", title="Basketball news", url="https://example.com/2", 
                  date="2025-06-20", source="The Guardian", summary="Lakers won"),
            Story(story_id="3", title="Chelsea transfer", url="https://example.com/3", 
                  date="2025-06-20", source="Sky Sports", summary="Chelsea signed player"),
        ]
        
        source_types = {
            "1": "confirmed",  # Should skip check
            "2": "accepted",   # Should fail check
            "3": "accepted"    # Should pass check
        }
        
        processed_stories, stats = checker.check_stories(stories, source_types)
        
        assert len(processed_stories) == 3
        assert stats["total"] == 3
        assert stats["confirmed_skipped"] == 1
        assert stats["relevant"] == 1
        assert stats["not_relevant"] == 1
        
        # Check individual story statuses
        story1, story2, story3 = processed_stories
        
        # Story 1 (confirmed) should be marked as skipped
        assert story1.relevance_status == RelevanceStatus.relevant
        assert "Confirmed source" in story1.relevance_reason
        
        # Story 2 (accepted, not relevant) should be marked as not relevant
        assert story2.relevance_status == RelevanceStatus.not_relevant
        assert "No relevance keywords found" in story2.relevance_reason
        
        # Story 3 (accepted, relevant) should be marked as relevant
        assert story3.relevance_status == RelevanceStatus.relevant
        assert "Matched relevance keywords" in story3.relevance_reason
    
    def test_unknown_strategy_fallback(self):
        """Test that unknown strategy falls back to substring."""
        config = {
            "relevance_checker": {
                "keywords": ["Chelsea"],
                "strategy": "unknown_strategy"
            }
        }
        
        checker = RelevanceChecker(config)
        
        story = Story(
            story_id="8",
            title="Chelsea FC news",
            url="https://example.com/8",
            date="2025-06-20",
            source="The Guardian",
            summary="Chelsea won the match"
        )
        
        is_relevant, reason = checker.is_relevant(story, "accepted")
        
        # Should still work with substring matching
        assert is_relevant is True
        assert "chelsea" in reason
