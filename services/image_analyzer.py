"""
Image Analyzer Service

This module provides functionality to detect and analyze images from Reddit posts
using vision-capable LLM models.
"""

import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import IMAGE_ANALYSIS_CONFIG, LLM_PROVIDERS, REDDIT_COLLECTION_CONFIG
from services.llm_processing.core.prompt_loader import PromptLoader

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ImageAnalyzer:
    """Service for detecting and analyzing images from Reddit posts."""

    # Image file extensions
    IMAGE_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"
    ]

    def __init__(self):
        """Initialize the Image Analyzer."""
        # Use REDDIT_COLLECTION_CONFIG as single source of truth
        self.enabled = REDDIT_COLLECTION_CONFIG.get("analyze_images", False)
        self.prompt_loader = PromptLoader()

        if not self.enabled:
            logger.info("Image analysis is disabled")
            return

        # Get OpenRouter API key
        openrouter_config = LLM_PROVIDERS.get("openrouter", {})
        self.api_key = openrouter_config.get("api_key")

        if not self.api_key:
            logger.warning("OpenRouter API key not found - image analysis will be disabled")
            self.enabled = False
            return

        # Initialize OpenAI client with OpenRouter
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

        # Get configuration
        self.primary_model = IMAGE_ANALYSIS_CONFIG.get("model", "qwen/qwen2.5-vl-72b-instruct:free")
        self.fallback_models = IMAGE_ANALYSIS_CONFIG.get("fallback_models", [])
        self.max_tokens = IMAGE_ANALYSIS_CONFIG.get("max_tokens", 500)

        logger.info(f"Image Analyzer initialized with primary model: {self.primary_model}")
        logger.info(f"Fallback models: {', '.join(self.fallback_models)}")

    def is_image_url(self, url: str) -> bool:
        """
        Check if a URL points to an image.

        Args:
            url: URL to check

        Returns:
            True if URL is an image, False otherwise
        """
        if not url:
            return False

        url_lower = url.lower()

        # Check if URL ends with image extension
        for ext in self.IMAGE_EXTENSIONS:
            if url_lower.endswith(ext):
                return True

        return False

    def analyze_image(self, image_url: str, custom_prompt: Optional[str] = None) -> Optional[str]:
        """
        Analyze an image and return a description.
        Uses OpenRouter's automatic fallback mechanism via extra_body.models.

        Args:
            image_url: URL of the image to analyze
            custom_prompt: Optional custom prompt (uses default if not provided)

        Returns:
            Image description or None if analysis fails
        """
        if not self.enabled:
            logger.debug("Image analysis is disabled")
            return None

        if not self.is_image_url(image_url):
            logger.debug(f"URL is not an image: {image_url}")
            return None

        # Generate prompt from template (or use custom prompt if provided)
        prompt = custom_prompt or self.prompt_loader.get_image_analysis_prompt()

        try:
            logger.info(f"Analyzing image with primary model '{self.primary_model}': {image_url}")

            # Call the vision model with automatic fallback
            # OpenRouter will automatically try fallback models if primary fails
            response = self.client.chat.completions.create(
                model=self.primary_model,
                extra_body={
                    "models": self.fallback_models
                },
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens
            )

            # Extract description
            description = response.choices[0].message.content

            if description:
                logger.info(f"✅ Successfully analyzed image ({len(description)} chars)")
                return description.strip()
            else:
                logger.warning(f"Empty response for image: {image_url}")
                return None

        except Exception as e:
            logger.error(f"❌ Error analyzing image {image_url}: {e}")
            return None

    def analyze_post(self, post: dict) -> Optional[str]:
        """
        Analyze image from a Reddit post if it contains one.

        Args:
            post: Post dictionary containing 'url' field

        Returns:
            Image description or None if no image or analysis fails
        """
        url = post.get("url")
        if not url:
            return None

        return self.analyze_image(url)


# Singleton instance
_image_analyzer = None


def get_image_analyzer() -> ImageAnalyzer:
    """
    Get or create the singleton ImageAnalyzer instance.

    Returns:
        ImageAnalyzer instance
    """
    global _image_analyzer
    if _image_analyzer is None:
        _image_analyzer = ImageAnalyzer()
    return _image_analyzer


if __name__ == "__main__":
    """Simple test for ImageAnalyzer."""
    print("=" * 80)
    print("Testing Image Analyzer")
    print("=" * 80)

    # Test URLs
    test_urls = [
        "https://i.redd.it/d2rcvb6nyvsf1.jpeg",  # Image URL
        "https://www.reddit.com/r/test",  # Not an image
        "https://i.redd.it/0w8kjy34z5ke1.png",  # Image extension
    ]

    analyzer = get_image_analyzer()

    if not analyzer.enabled:
        print("❌ Image analysis is disabled (check API key)")
        exit(1)

    for url in test_urls:
        print(f"\n{'='*80}")
        print(f"Testing URL: {url}")
        print(f"Is image: {analyzer.is_image_url(url)}")

        if analyzer.is_image_url(url):
            description = analyzer.analyze_image(url)
            if description:
                print(f"\n📝 Description:\n{description}")
            else:
                print("❌ Failed to analyze image")

    print(f"\n{'='*80}")
    print("✅ Test completed")
