"""
Image Enricher

This module enriches Reddit posts with image analysis data.
Checks database cache first to avoid redundant API calls.
"""

import logging
from typing import List, Optional
from ..models import RedditPost

logger = logging.getLogger(__name__)


class ImageEnricher:
    """Enriches posts with image analysis data."""

    def __init__(self, image_analyzer, db_client=None):
        """
        Initialize the image enricher.

        Args:
            image_analyzer: ImageAnalyzer instance from services.image_analyzer
            db_client: Optional MongoDB client for caching
        """
        self.image_analyzer = image_analyzer
        self.db_client = db_client
        self.stats = {
            "analyzed": 0,
            "cached": 0,
            "skipped": 0
        }

    def enrich_post(self, post: RedditPost, existing_post: Optional[dict] = None) -> RedditPost:
        """
        Enrich a single post with image analysis.

        Args:
            post: RedditPost to enrich
            existing_post: Optional existing post from database (to avoid duplicate queries)

        Returns:
            Enriched RedditPost
        """
        if not self.image_analyzer.enabled:
            self.stats["skipped"] += 1
            return post

        # Check if URL is an image
        if not self.image_analyzer.is_image_url(post.url):
            self.stats["skipped"] += 1
            return post

        # Check for cached analysis
        if existing_post and "photo_parse" in existing_post:
            # Use cached analysis from database
            post.photo_parse = existing_post["photo_parse"]
            self.stats["cached"] += 1
            logger.info(f"Using cached photo_parse for post {post.post_id}")
            return post

        # Query database if not already provided
        if existing_post is None and self.db_client:
            existing_post = self.db_client.get_post_by_id(post.post_id)
            if existing_post and "photo_parse" in existing_post:
                post.photo_parse = existing_post["photo_parse"]
                self.stats["cached"] += 1
                logger.info(f"Using cached photo_parse for post {post.post_id}")
                return post

        # No cache found - analyze image
        photo_description = self.image_analyzer.analyze_image(post.url)
        if photo_description:
            post.photo_parse = photo_description
            self.stats["analyzed"] += 1
            logger.info(f"Added new photo_parse for post {post.post_id}")
        else:
            self.stats["skipped"] += 1

        return post

    def enrich_posts(self, posts: List[RedditPost]) -> List[RedditPost]:
        """
        Enrich multiple posts with image analysis.

        Args:
            posts: List of RedditPost objects to enrich

        Returns:
            List of enriched RedditPost objects
        """
        logger.info(f"Enriching {len(posts)} posts with image analysis")

        # Reset stats
        self.stats = {"analyzed": 0, "cached": 0, "skipped": 0}

        enriched_posts = []
        for post in posts:
            enriched_post = self.enrich_post(post)
            enriched_posts.append(enriched_post)

        logger.info(
            f"Image enrichment complete - "
            f"Analyzed: {self.stats['analyzed']}, "
            f"Cached: {self.stats['cached']}, "
            f"Skipped: {self.stats['skipped']}"
        )

        return enriched_posts

    def get_stats(self) -> dict:
        """
        Get enrichment statistics.

        Returns:
            Dictionary with enrichment stats
        """
        return self.stats.copy()
