"""
Web Content Enricher
Scrapes web pages using Firecrawl and generates summaries using LLM
"""
import logging
import sys
import os
from typing import Optional
from firecrawl import Firecrawl
from openai import OpenAI

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.llm_processing.core.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class WebContentEnricher:
    """Enriches posts with web page content summaries"""

    # URLs to exclude (already handled by other enrichers)
    EXCLUDED_PATTERNS = [
        'reddit.com',
        'redd.it',  # Reddit images/videos
        'youtu.be',
        'youtube.com',
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'  # Images (handled by ImageEnricher)
    ]

    def __init__(
        self,
        firecrawl_api_key: str,
        openrouter_api_key: str,
        model: str = "deepseek/deepseek-chat-v3.1:free",
        max_tokens: int = 500,
        enabled: bool = True
    ):
        """
        Initialize Web Content enricher

        Args:
            firecrawl_api_key: Firecrawl API key
            openrouter_api_key: OpenRouter API key for LLM summarization
            model: LLM model to use for summarization
            max_tokens: Maximum tokens for summary
            enabled: Whether this enricher is enabled
        """
        self.enabled = enabled
        self.model = model
        self.max_tokens = max_tokens
        self.prompt_loader = PromptLoader()

        if self.enabled:
            self.firecrawl = Firecrawl(api_key=firecrawl_api_key)
            self.llm_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key
            )
            logger.info(f"WebContentEnricher initialized (enabled={enabled}, model={model})")
        else:
            self.firecrawl = None
            self.llm_client = None
            logger.info("WebContentEnricher disabled")

    def should_scrape(self, url: str) -> bool:
        """
        Check if URL should be scraped

        Args:
            url: URL to check

        Returns:
            True if should scrape, False otherwise
        """
        url_lower = url.lower()

        # Check exclusion patterns
        for pattern in self.EXCLUDED_PATTERNS:
            if pattern in url_lower:
                return False

        # Only scrape http/https URLs
        if not (url.startswith('http://') or url.startswith('https://')):
            return False

        return True

    def scrape_content(self, url: str) -> Optional[str]:
        """
        Scrape content from URL using Firecrawl

        Args:
            url: URL to scrape

        Returns:
            Markdown content or None if failed
        """
        if not self.firecrawl:
            logger.warning("WebContentEnricher not initialized (disabled)")
            return None

        try:
            logger.info(f"Scraping content from {url}")
            doc = self.firecrawl.scrape(url)

            if not doc or not hasattr(doc, 'markdown'):
                logger.warning(f"No markdown content returned for {url}")
                return None

            content = doc.markdown

            if not content or len(content.strip()) == 0:
                logger.warning(f"Empty content returned for {url}")
                return None

            logger.info(f"Successfully scraped {url} ({len(content)} characters)")
            return content

        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None

    def summarize_content(self, content: str, url: str) -> Optional[str]:
        """
        Generate summary of web content using LLM

        Args:
            content: Markdown content
            url: Source URL (for context)

        Returns:
            Summary text or None if failed
        """
        if not self.llm_client:
            logger.warning("WebContentEnricher LLM client not initialized")
            return None

        try:
            # Truncate content if too long (to avoid token limits)
            max_content_length = 150000  # ~40000 tokens
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
                logger.info(f"Truncated content to {max_content_length} characters")

            # Generate prompt from template
            prompt = self.prompt_loader.get_web_content_summary_prompt(url, content)

            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3
            )

            summary = response.choices[0].message.content

            if not summary or len(summary.strip()) == 0:
                logger.warning(f"Empty summary returned for {url}")
                return None

            logger.info(f"Successfully generated summary ({len(summary)} characters)")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error generating summary for {url}: {e}")
            return None

    def enrich_post(self, post, existing_post: Optional[dict] = None):
        """
        Enrich a post with web content summary if applicable

        Args:
            post: RedditPost object
            existing_post: Existing post from database (for caching)

        Returns:
            RedditPost object (with web_content_summary as extra attribute)
        """
        # Skip if enricher is disabled
        if not self.enabled:
            return post

        # Check if already have cached summary
        if existing_post and 'web_content_summary' in existing_post:
            post.web_content_summary = existing_post['web_content_summary']
            logger.info(f"Using cached web content summary for post {post.post_id}")
            return post

        # Check if URL should be scraped
        if not self.should_scrape(post.url):
            logger.debug(f"Skipping URL (excluded pattern): {post.url}")
            return post

        logger.info(f"Processing web content: {post.url}")

        # Scrape content
        content = self.scrape_content(post.url)
        if not content:
            logger.info(f"No content scraped from {post.url}, skipping")
            return post

        # Generate summary
        summary = self.summarize_content(content, post.url)
        if not summary:
            logger.info(f"Failed to generate summary for {post.url}, skipping")
            return post

        # Success! Add to post as extra attribute
        post.web_content_summary = summary
        logger.info(f"Successfully enriched post {post.post_id} with web content summary")

        return post
