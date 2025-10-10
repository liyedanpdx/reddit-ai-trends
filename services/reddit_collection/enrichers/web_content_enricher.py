"""
Web Content Enricher
Scrapes web pages using Firecrawl and generates summaries using LLM
"""
import logging
import sys
import os
from typing import Optional
from firecrawl import FirecrawlApp
from openai import OpenAI

# Add project root to path for imports
# web_content_enricher.py is at: services/reddit_collection/enrichers/
# Project root is 4 levels up
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
        model: str = "qwen/qwen3-235b-a22b:free",
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
            self.firecrawl = FirecrawlApp(api_key=firecrawl_api_key)
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


if __name__ == "__main__":
    """Test Web Content Enricher"""
    # Add project root to path for standalone execution
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from dotenv import load_dotenv

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Load environment variables
    load_dotenv()

    print("=" * 80)
    print("Testing Web Content Enricher")
    print("=" * 80)

    # Test URLs
    test_urls = [
        "https://www.uni-koeln.de/en/university/news/news/news-detail/antibody-discovered-that-blocks-almost-all-known-hiv-variants-in-neutralization-assays",
        "https://github.com/liyedanpdx/reddit-ai-trends/blob/main/reports/2025/10/05/report_20251005_en.md",
        "https://www.reddit.com/r/LocalLLaMA"  # Should be excluded
    ]

    # Initialize enricher
    firecrawl_key = os.getenv("FIRECRAWL_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if not firecrawl_key:
        print("❌ FIRECRAWL_API_KEY not found in environment")
        exit(1)

    if not openrouter_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        exit(1)

    enricher = WebContentEnricher(
        firecrawl_api_key=firecrawl_key,
        openrouter_api_key=openrouter_key,
        model="qwen/qwen3-235b-a22b:free",
        max_tokens=500,
        enabled=True
    )

    print(f"\n✓ Enricher initialized")
    print(f"  - Model: {enricher.model}")
    print(f"  - Max tokens: {enricher.max_tokens}")

    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"Testing URL: {url}")
        print(f"{'='*80}")

        # Test should_scrape
        should_scrape = enricher.should_scrape(url)
        print(f"Should scrape: {should_scrape}")

        if not should_scrape:
            print("⏭️  Skipped (excluded pattern)")
            continue

        # Test scraping
        print("\n📥 Scraping content...")
        content = enricher.scrape_content(url)

        if not content:
            print("❌ Failed to scrape content")
            continue

        print(f"✓ Scraped {len(content)} characters")
        print(f"\nFirst 200 chars:\n{content[:200]}...")

        # Test summarization
        print("\n🤖 Generating summary...")
        summary = enricher.summarize_content(content, url)

        if not summary:
            print("❌ Failed to generate summary")
            continue

        print(f"✓ Generated summary ({len(summary)} characters)")
        print(f"\n📝 Summary:\n{summary}")

    print(f"\n{'='*80}")
    print("✅ Test completed")
    print(f"{'='*80}")
