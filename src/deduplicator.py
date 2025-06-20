import logging
import hashlib
from typing import List, Dict, Set, Tuple
from urllib.parse import urlparse, parse_qs
from storage import Story

logger = logging.getLogger(__name__)

class StoryDeduplicator:
    """Handles deduplication of news stories using URL and headline hashes."""
    
    def __init__(self):
        self.url_hashes: Set[str] = set()
        self.headline_hashes: Set[str] = set()
        self.existing_story_ids: Set[str] = set()
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication by removing tracking parameters and fragments.
        """
        try:
            parsed = urlparse(url)
            
            # Remove common tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'campaign_id',
                '_ga', '_gac', '_gid', 'mc_cid', 'mc_eid'
            }
            
            if parsed.query:
                params = parse_qs(parsed.query)
                filtered_params = {k: v for k, v in params.items() if k not in tracking_params}
                query_string = '&'.join(f"{k}={v[0]}" for k, v in filtered_params.items())
            else:
                query_string = ""
            
            # Reconstruct URL without fragment and with filtered parameters
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if query_string:
                normalized += f"?{query_string}"
            
            return normalized.lower()
            
        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return url.lower()
    
    def _normalize_headline(self, headline: str) -> str:
        """
        Normalize headline for deduplication by removing common variations.
        """
        # Remove extra whitespace and convert to lowercase
        normalized = ' '.join(headline.lower().split())
        
        # Remove common punctuation that might vary
        punctuation_to_remove = ['"', "'", '"', '"', ''', ''']
        for punct in punctuation_to_remove:
            normalized = normalized.replace(punct, '')
        
        # Remove trailing punctuation that might vary
        normalized = normalized.rstrip('.,!?;:')
        
        return normalized
    
    def _get_url_hash(self, url: str) -> str:
        """Generate hash for normalized URL."""
        normalized_url = self._normalize_url(url)
        return hashlib.md5(normalized_url.encode('utf-8')).hexdigest()
    
    def _get_headline_hash(self, headline: str) -> str:
        """Generate hash for normalized headline."""
        normalized_headline = self._normalize_headline(headline)
        return hashlib.md5(normalized_headline.encode('utf-8')).hexdigest()
    
    def _is_google_news_redirect(self, url: str) -> bool:
        """Check if URL is a Google News redirect URL."""
        return 'news.google.com' in url and '/articles/' in url
    
    def load_existing_stories(self, existing_stories: List[Story]) -> None:
        """
        Load existing stories to build deduplication index.
        """
        logger.info(f"Loading {len(existing_stories)} existing stories for deduplication")
        
        self.url_hashes.clear()
        self.headline_hashes.clear()
        self.existing_story_ids.clear()
        
        for story in existing_stories:
            # Add story ID
            self.existing_story_ids.add(story.story_id)
            
            # Add URL hash (skip Google News redirects as they're not reliable)
            if not self._is_google_news_redirect(story.url):
                url_hash = self._get_url_hash(story.url)
                self.url_hashes.add(url_hash)
            
            # Add headline hash
            headline_hash = self._get_headline_hash(story.title)
            self.headline_hashes.add(headline_hash)
        
        logger.info(f"Deduplication index loaded: {len(self.url_hashes)} URL hashes, "
                   f"{len(self.headline_hashes)} headline hashes, "
                   f"{len(self.existing_story_ids)} story IDs")
    
    def deduplicate_stories(self, stories: List[Story]) -> Tuple[List[Story], Dict[str, int]]:
        """
        Remove duplicate stories from the list.
        Returns (unique_stories, dedup_stats)
        """
        logger.info(f"Starting deduplication of {len(stories)} stories")
        
        unique_stories: List[Story] = []
        dedup_stats = {
            'total_input': len(stories),
            'duplicates_by_story_id': 0,
            'duplicates_by_url': 0,
            'duplicates_by_headline': 0,
            'unique_output': 0
        }
        
        # Track hashes for new stories to avoid duplicates within the same batch
        batch_url_hashes: Set[str] = set()
        batch_headline_hashes: Set[str] = set()
        batch_story_ids: Set[str] = set()
        
        for story in stories:
            is_duplicate = False
            duplicate_reason = ""
            
            # Check for story ID duplicates (existing and within batch)
            if story.story_id in self.existing_story_ids or story.story_id in batch_story_ids:
                is_duplicate = True
                duplicate_reason = "story_id"
                dedup_stats['duplicates_by_story_id'] += 1
            
            # Check for URL duplicates (skip Google News redirects)
            elif not self._is_google_news_redirect(story.url):
                url_hash = self._get_url_hash(story.url)
                if url_hash in self.url_hashes or url_hash in batch_url_hashes:
                    is_duplicate = True
                    duplicate_reason = "url"
                    dedup_stats['duplicates_by_url'] += 1
                else:
                    batch_url_hashes.add(url_hash)
            
            # Check for headline duplicates (if not already marked as duplicate)
            if not is_duplicate:
                headline_hash = self._get_headline_hash(story.title)
                if headline_hash in self.headline_hashes or headline_hash in batch_headline_hashes:
                    is_duplicate = True
                    duplicate_reason = "headline"
                    dedup_stats['duplicates_by_headline'] += 1
                else:
                    batch_headline_hashes.add(headline_hash)
            
            if is_duplicate:
                logger.debug(f"DUPLICATE ({duplicate_reason}): {story.title[:50]}... [{story.source}]")
            else:
                unique_stories.append(story)
                batch_story_ids.add(story.story_id)
                logger.debug(f"UNIQUE: {story.title[:50]}... [{story.source}]")
        
        dedup_stats['unique_output'] = len(unique_stories)
        
        logger.info(f"Deduplication complete: {dedup_stats['total_input']} input stories, "
                   f"{dedup_stats['unique_output']} unique stories remaining")
        logger.info(f"Removed duplicates: {dedup_stats['duplicates_by_story_id']} by story_id, "
                   f"{dedup_stats['duplicates_by_url']} by URL, "
                   f"{dedup_stats['duplicates_by_headline']} by headline")
        
        return unique_stories, dedup_stats
