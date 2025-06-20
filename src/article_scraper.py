import logging
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import time
from urllib.parse import urlparse
from typechecking import as_int, as_dict
import unicodedata
import re

# Import various scraping libraries for fallback handling
try:
    from newspaper import Article
    NEWSPAPER_AVAILABLE = True
except ImportError:
    NEWSPAPER_AVAILABLE = False
    logging.warning("newspaper3k not available - install with: pip install newspaper3k")

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False
    logging.warning("BeautifulSoup not available - install with: pip install beautifulsoup4")

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logging.warning("trafilatura not available - install with: pip install trafilatura")

# Optional language detection
try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    logging.warning("langdetect not available - install with: pip install langdetect")

from storage import Story, ScrapingStatus

logger = logging.getLogger(__name__)

class ArticleScraper:
    """Scrapes full article content from URLs with multiple fallback strategies."""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3, delay_between_requests: float = 1.0):
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay_between_requests = delay_between_requests
        
        # User agent to avoid being blocked
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        logger.info(f"Initialized ArticleScraper with timeout={timeout}s, max_retries={max_retries}")
        self._log_available_scrapers()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text to English Unicode."""
        try:
            # Remove non-printable characters
            text = ''.join(char for char in text if char.isprintable() or char.isspace())
            
            # Normalize Unicode (NFD normalization, then filter out combining characters)
            text = unicodedata.normalize('NFD', text)
            text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
            
            # Clean up excessive whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text
        except Exception as e:
            logger.warning(f"Text normalization failed: {e}")
            return text.strip()
    
    def _detect_language(self, text: str) -> Optional[str]:
        """Detect language of text. Returns language code or None if detection fails."""
        if not LANGDETECT_AVAILABLE or not text or len(text.strip()) < 50:
            return None
        
        try:
            # Use first 1000 characters for language detection (faster and usually sufficient)
            sample_text = text[:1000].strip()
            language = detect(sample_text)
            logger.debug(f"Detected language: {language}")
            return language
        except Exception as e:
            logger.debug(f"Language detection failed: {e}")
            return None
    
    def _needs_translation(self, text: str) -> bool:
        """Check if text needs translation to English."""
        detected_lang = self._detect_language(text)
        if not detected_lang:
            # If we can't detect language, assume it's English
            return False
        
        # Consider text as needing translation if it's not English
        return detected_lang != 'en'
    
    def _log_available_scrapers(self):
        """Log which scraping libraries are available."""
        available = []
        if NEWSPAPER_AVAILABLE:
            available.append("newspaper3k")
        if BS4_AVAILABLE:
            available.append("beautifulsoup4")
        if TRAFILATURA_AVAILABLE:
            available.append("trafilatura")
        
        logger.info(f"Available scraping libraries: {', '.join(available) if available else 'None (basic scraping only)'}")
    
    def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch raw HTML content from URL with retries."""
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Fetching HTML from {url} (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.get(url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                
                logger.debug(f"Successfully fetched {len(response.text)} characters from {url}")
                return response.text
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.delay_between_requests * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {url}")
                    return None
        
        return None
    
    def _scrape_with_newspaper(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Scrape article using newspaper3k library with aggressive extraction."""
        if not NEWSPAPER_AVAILABLE:
            return None
        
        try:
            logger.debug(f"Attempting to scrape with newspaper3k: {url}")
            
            # Try multiple newspaper3k strategies
            strategies = [
                self._newspaper_strategy_html,
                self._newspaper_strategy_download,
                self._newspaper_strategy_aggressive
            ]
            
            for i, strategy in enumerate(strategies, 1):
                try:
                    logger.debug(f"Trying newspaper3k strategy {i}/3")
                    result = strategy(url, html)
                    if result and result.get('text') and len(result['text'].strip()) > 500:
                        logger.debug(f"newspaper3k strategy {i} extracted {len(result['text'])} characters")
                        return result
                except Exception as e:
                    logger.debug(f"newspaper3k strategy {i} failed: {e}")
                    continue
            
            logger.debug("All newspaper3k strategies failed")
            return None
                
        except Exception as e:
            logger.debug(f"newspaper3k failed: {e}")
            return None
    
    def _newspaper_strategy_html(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Standard newspaper3k strategy using provided HTML."""
        article = Article(url)
        article.set_html(html)
        article.parse()
        
        return {
            'title': article.title,
            'text': article.text,
            'authors': article.authors,
            'publish_date': article.publish_date.isoformat() if article.publish_date else None,
            'top_image': article.top_image,
            'meta_description': article.meta_description,
            'meta_keywords': article.meta_keywords,
            'summary': getattr(article, 'summary', None),
            'scraper': 'newspaper3k-html'
        }
    
    def _newspaper_strategy_download(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Newspaper3k strategy using fresh download (sometimes gets more content)."""
        article = Article(url)
        article.download()
        article.parse()
        
        return {
            'title': article.title,
            'text': article.text,
            'authors': article.authors,
            'publish_date': article.publish_date.isoformat() if article.publish_date else None,
            'top_image': article.top_image,
            'meta_description': article.meta_description,
            'meta_keywords': article.meta_keywords,
            'summary': getattr(article, 'summary', None),
            'scraper': 'newspaper3k-download'
        }
    
    def _newspaper_strategy_aggressive(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Aggressive newspaper3k strategy with custom configuration."""
        from newspaper import Config
        
        # Create aggressive config
        config = Config()
        config.browser_user_agent = self.headers['User-Agent']
        config.request_timeout = self.timeout
        config.number_threads = 1
        config.verbose = False
        config.fetch_images = False
        config.memoize_articles = False
        config.use_meta_language = True
        
        article = Article(url, config=config)
        article.set_html(html)
        article.parse()
        
        # If we didn't get much content, try to extract more aggressively
        text = article.text
        if not text or len(text.strip()) < 100:
            # Try extracting from article's clean_doc if available
            if hasattr(article, 'clean_doc') and article.clean_doc is not None:
                from newspaper.extractors import ContentExtractor
                extractor = ContentExtractor(config)
                try:
                    text = extractor.get_text(article.clean_doc)
                except Exception as e:
                    logger.debug(f"ContentExtractor failed: {e}")
                    pass
        
        return {
            'title': article.title,
            'text': text,
            'authors': article.authors,
            'publish_date': article.publish_date.isoformat() if article.publish_date else None,
            'top_image': article.top_image,
            'meta_description': article.meta_description,
            'meta_keywords': article.meta_keywords,
            'summary': getattr(article, 'summary', None),
            'scraper': 'newspaper3k-aggressive'
        }
    
    def _scrape_with_trafilatura(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Scrape article using trafilatura library with aggressive extraction."""
        if not TRAFILATURA_AVAILABLE:
            return None
        
        try:
            logger.debug(f"Attempting to scrape with trafilatura: {url}")
            
            # Try multiple trafilatura strategies
            strategies = [
                self._trafilatura_strategy_standard,
                self._trafilatura_strategy_aggressive,
                self._trafilatura_strategy_fallback
            ]
            
            for i, strategy in enumerate(strategies, 1):
                try:
                    logger.debug(f"Trying trafilatura strategy {i}/3")
                    result = strategy(url, html)
                    if result and result.get('text') and len(result['text'].strip()) > 500:
                        logger.debug(f"trafilatura strategy {i} extracted {len(result['text'])} characters")
                        return result
                except Exception as e:
                    logger.debug(f"trafilatura strategy {i} failed: {e}")
                    continue
            
            logger.debug("All trafilatura strategies failed")
            return None
                
        except Exception as e:
            logger.debug(f"trafilatura failed: {e}")
            return None
    
    def _trafilatura_strategy_standard(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Standard trafilatura extraction."""
        text = trafilatura.extract(html, include_comments=False, include_tables=False)
        metadata = trafilatura.extract_metadata(html)
        
        return {
            'title': metadata.title if metadata else None,
            'text': text,
            'authors': [metadata.author] if metadata and metadata.author else [],
            'publish_date': metadata.date if metadata else None,
            'meta_description': metadata.description if metadata else None,
            'scraper': 'trafilatura-standard'
        }
    
    def _trafilatura_strategy_aggressive(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Aggressive trafilatura extraction with more permissive settings."""
        # More aggressive extraction settings
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,  # Include tables
            include_links=True,   # Include links text
            include_images=False,
            favor_recall=True,    # Favor getting more content over precision
            no_fallback=False,    # Enable fallback extraction
            with_metadata=True
        )
        
        metadata = trafilatura.extract_metadata(html)
        
        return {
            'title': metadata.title if metadata else None,
            'text': text,
            'authors': [metadata.author] if metadata and metadata.author else [],
            'publish_date': metadata.date if metadata else None,
            'meta_description': metadata.description if metadata else None,
            'scraper': 'trafilatura-aggressive'
        }
    
    def _trafilatura_strategy_fallback(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Trafilatura with fallback and bare extraction."""
        # Use bare extraction as fallback
        text = trafilatura.bare_extraction(html)
        if text and isinstance(text, dict):
            content = text.get('text', '')
            title = text.get('title', '')
            
            return {
                'title': title,
                'text': content,
                'authors': [],
                'publish_date': None,
                'meta_description': None,
                'scraper': 'trafilatura-fallback'
            }
        
        return None
    
    def _scrape_with_beautifulsoup(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Scrape article using BeautifulSoup with heuristic content extraction."""
        if not BS4_AVAILABLE:
            return None
        
        try:
            logger.debug(f"Attempting to scrape with BeautifulSoup: {url}")
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'advertisement']):
                element.decompose()
            
            # Try to find article content using common patterns
            content_selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.article-body',
                '.post-content',
                '.entry-content',
                '.content',
                '#content',
                '.main-content'
            ]
            
            text = None
            title = None
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
            
            # Try each content selector
            for selector in content_selectors:
                try:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        text = content_elem.get_text(separator=' ', strip=True)
                        if text and len(text) > 700:  # Higher threshold for basic scraping
                            break
                except Exception:
                    continue
            
            # Fallback: get all paragraph text
            if not text or len(text) < 700:
                paragraphs = soup.find_all('p')
                text = ' '.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            if text and len(text.strip()) > 500:
                result: Dict[str, Any] = {
                    'title': title,
                    'text': text.strip(),
                    'authors': [],
                    'publish_date': None,
                    'scraper': 'beautifulsoup4'
                }
                
                logger.debug(f"BeautifulSoup extracted {len(text)} characters")
                return result
            else:
                logger.debug("BeautifulSoup didn't extract enough content")
                return None
                
        except Exception as e:
            logger.debug(f"BeautifulSoup failed: {e}")
            return None
    
    def _scrape_basic_fallback(self, url: str, html: str) -> Optional[Dict[str, Any]]:
        """Basic fallback scraping using simple text extraction."""
        try:
            logger.debug(f"Attempting basic fallback scraping: {url}")
            
            # Very basic HTML stripping
            import re
            
            # Remove script and style elements
            html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL | re.IGNORECASE)
            
            # Extract title
            title_match = re.search(r'<title[^>]*>(.*?)</title>', html_clean, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else None
            
            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_clean)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            if text and len(text) > 200:
                result: Dict[str, Any] = {
                    'title': title,
                    'text': text[:10000],  # Limit to first 10k chars to avoid too much noise
                    'authors': [],
                    'publish_date': None,
                    'scraper': 'basic_fallback'
                }
                if result['text']:
                    logger.debug(f"Basic fallback extracted {len(result['text'])} characters")
                else:
                    logger.debug("Basic fallback extracted no text")
                return result
            else:
                logger.debug("Basic fallback didn't extract enough content")
                return None
                
        except Exception as e:
            logger.debug(f"Basic fallback failed: {e}")
            return None
    
    def scrape_article(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape article content from URL using multiple fallback strategies.
        Returns article data or None if all methods fail.
        """
        logger.info(f"Starting article scraping for: {url}")
        
        # Track errors from each scraping method
        scraping_errors: Dict[str, Any] = {}
        
        # Validate URL
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logger.error(f"Invalid URL format: {url}")
                return {"errors": {"url_validation": f"Invalid URL format: {url}"}}
        except Exception as e:
            logger.error(f"URL parsing failed: {e}")
            return {"errors": {"url_validation": f"URL parsing failed: {e}"}}
        
        # Fetch HTML
        html = self._fetch_html(url)
        if not html:
            logger.error(f"Failed to fetch HTML from {url}")
            return {"errors": {"html_fetch": "Failed to fetch HTML from URL"}}
        
        # Try scraping methods in order of preference
        scraping_methods = [
            ("newspaper3k", self._scrape_with_newspaper),
            ("trafilatura", self._scrape_with_trafilatura), 
            ("beautifulsoup4", self._scrape_with_beautifulsoup),
            ("basic_fallback", self._scrape_basic_fallback)
        ]
        
        for method_name, method in scraping_methods:
            try:
                result = method(url, html)
                if result and result.get('text'):
                    # Normalize text to English Unicode
                    result['text'] = self._normalize_text(result['text'])
                    
                    # Detect language and add metadata
                    detected_language = self._detect_language(result['text'])
                    result['detected_language'] = detected_language
                    result['needs_translation'] = self._needs_translation(result['text'])
                    
                    logger.info(f"Successfully scraped article using {result['scraper']}: "
                              f"{len(result['text'])} characters extracted")
                    
                    if detected_language:
                        logger.info(f"Detected language: {detected_language}, needs translation: {result['needs_translation']}")
                    
                    # Add scraping metadata
                    result['scraped_at'] = datetime.now().isoformat()
                    result['url'] = url
                    result['content_length'] = len(result['text'])
                    result['errors'] = scraping_errors  # Include any partial errors
                    
                    return result
                else:
                    # Method didn't extract enough content
                    error_msg = f"{method_name} didn't extract enough content"
                    scraping_errors[method_name] = error_msg
                    logger.debug(error_msg)
                    
            except Exception as e:
                error_msg = f"{method_name} failed: {e}"
                scraping_errors[method_name] = error_msg
                logger.warning(error_msg)
                continue
        
        logger.error(f"All scraping methods failed for {url}")
        return {"errors": scraping_errors}
    
    def scrape_stories(self, stories: List[Story]) -> tuple[List[Story], Dict[str, Any]]:
        """
        Scrape article content for multiple stories.
        Returns (updated_stories, scraping_stats)
        """
        logger.info(f"Starting article scraping for {len(stories)} stories")
        
        scraping_stats = {
            "total_stories": len(stories),
            "successfully_scraped": 0,
            "scraping_failures": 0,
            "already_scraped": 0,
            "scrapers_used": {}
        }
        
        updated_stories = []
        
        for i, story in enumerate(stories, 1):
            try:
                # Check if story already has full text
                if story.full_text and len(story.full_text.strip()) > 50:
                    logger.debug(f"Story {i}: Already has full text, skipping scraping")
                    story.scraping_status = ScrapingStatus.skipped
                    story.scraping_error = None
                    scraping_stats["already_scraped"] = as_int(scraping_stats["already_scraped"])+1
                    updated_stories.append(story)
                    continue
                
                # Scrape the article
                logger.debug(f"Story {i}: Scraping {story.url}")
                article_data = self.scrape_article(story.url)
                
                if article_data and article_data.get('text'):
                    # Update story with scraped content
                    story.full_text = article_data['text']
                    story.scraping_status = ScrapingStatus.success
                    story.scraping_error = article_data.get('errors')  # Store any partial errors
                    story.scraper_used = article_data.get('scraper', 'unknown')
                    
                    # Update other fields if they're better than what we have
                    if article_data.get('title') and (not story.title or len(article_data['title']) > len(story.title)):
                        story.title = article_data['title']
                    
                    if article_data.get('authors') and not story.byline:
                        story.byline = ', '.join(article_data['authors'])
                    
                    # Store language detection results in description for now 
                    # (until we add proper fields to Story model)
                    if article_data.get('detected_language'):
                        lang_info = f"Language: {article_data['detected_language']}"
                        if article_data.get('needs_translation'):
                            lang_info += " (needs translation)"
                        
                        if story.description:
                            story.description += f" | {lang_info}"
                        else:
                            story.description = lang_info
                    
                    scraping_stats["successfully_scraped"] = as_int(scraping_stats['successfully_scraped']) +  1
                    
                    # Track which scraper was used
                    scraper_used = article_data.get('scraper', 'unknown')
                    scrapers_used = as_dict(scraping_stats["scrapers_used"])
                    scrapers_used[scraper_used] = as_int(as_dict(scrapers_used).get(scraper_used, 0)) + 1
                    
                    logger.debug(f"Story {i}: Successfully scraped {len(article_data['text'])} characters using {scraper_used}")
                    
                    # Log translation needs
                    if article_data.get('needs_translation'):
                        logger.info(f"Story {i}: Article detected as {article_data.get('detected_language', 'unknown')} - will need translation")
                    
                else:
                    # Record scraping failure
                    story.scraping_status = ScrapingStatus.failed
                    if article_data and 'errors' in article_data:
                        story.scraping_error = article_data['errors']
                    else:
                        story.scraping_error = {"general": "All scraping methods failed to extract content"}
                    story.scraper_used = None
                    scraping_stats["scraping_failures"] = as_int(scraping_stats["scraping_failures"]) + 1
                    logger.warning(f"Story {i}: Failed to scrape content from {story.url}")
                
                updated_stories.append(story)
                
                # Rate limiting between requests
                if i < len(stories):  # Don't sleep after the last story
                    time.sleep(self.delay_between_requests)
                    
            except Exception as e:
                # Record scraping exception
                story.scraping_status = ScrapingStatus.failed
                story.scraping_error = {"exception": f"Exception during scraping: {str(e)}"}
                story.scraper_used = None
                logger.error(f"Error processing story {i} for scraping: {e}")
                updated_stories.append(story)  # Add story without modification
                scraping_stats["scraping_failures"] = as_int(scraping_stats["scraping_failures"]) + 1
        
        logger.info(f"Article scraping complete: {scraping_stats['successfully_scraped']} scraped, "
                   f"{scraping_stats['scraping_failures']} failed, {scraping_stats['already_scraped']} already had content")
        
        if scraping_stats["scrapers_used"]:
            logger.info(f"Scrapers used: {scraping_stats['scrapers_used']}")
        
        return updated_stories, scraping_stats
