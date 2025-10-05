"""
Comment Enricher

This module enriches Reddit posts with comment data based on smart fetching strategy.
Implements the smart comment mode logic.
"""

import logging
from typing import List
from ..models import RedditPost
from ..fetchers.comment_fetcher import CommentFetcher
from config import REDDIT_COLLECTION_CONFIG

logger = logging.getLogger(__name__)


class CommentEnricher:
    """Enriches posts with comment data based on fetching strategy."""

    def __init__(self, comment_fetcher: CommentFetcher):
        """
        Initialize the comment enricher.

        Args:
            comment_fetcher: CommentFetcher instance
        """
        self.comment_fetcher = comment_fetcher
        self.stats = {
            "fetched": 0,
            "skipped": 0
        }

    def enrich_post(
        self,
        post: RedditPost,
        fetch_mode: str = "smart",
        limit: int = 5
    ) -> RedditPost:
        """
        Enrich a single post with comments based on fetching mode.

        Args:
            post: RedditPost to enrich
            fetch_mode: Fetching mode ("true", "false", "smart")
            limit: Maximum number of comments to fetch

        Returns:
            Enriched RedditPost
        """
        should_fetch = self._should_fetch_comments(post, fetch_mode)

        if should_fetch:
            comments = self.comment_fetcher.fetch_top_comments(post.post_id, limit)
            post.comments = comments
            self.stats["fetched"] += 1
            logger.debug(f"Fetched {len(comments)} comments for post {post.post_id}")
        else:
            post.comments = []
            self.stats["skipped"] += 1
            logger.debug(f"Skipped comments for post {post.post_id} (sufficient text content)")

        return post

    def enrich_posts(
        self,
        posts: List[RedditPost],
        fetch_mode: str = "smart",
        limit: int = 5
    ) -> List[RedditPost]:
        """
        Enrich multiple posts with comments.

        Args:
            posts: List of RedditPost objects to enrich
            fetch_mode: Fetching mode ("true", "false", "smart")
            limit: Maximum number of comments per post

        Returns:
            List of enriched RedditPost objects
        """
        logger.info(f"Enriching {len(posts)} posts with comments (mode={fetch_mode})")

        # Reset stats
        self.stats = {"fetched": 0, "skipped": 0}

        enriched_posts = []
        for post in posts:
            enriched_post = self.enrich_post(post, fetch_mode, limit)
            enriched_posts.append(enriched_post)

        logger.info(
            f"Comment enrichment complete - "
            f"Fetched: {self.stats['fetched']}, "
            f"Skipped: {self.stats['skipped']}"
        )

        return enriched_posts

    def _should_fetch_comments(self, post: RedditPost, fetch_mode: str) -> bool:
        """
        Determine if comments should be fetched based on mode.

        Args:
            post: RedditPost to check
            fetch_mode: Fetching mode ("true", "false", "smart")

        Returns:
            True if comments should be fetched, False otherwise
        """
        if fetch_mode == "true":
            return True
        elif fetch_mode == "false":
            return False
        elif fetch_mode == "smart":
            # Use RedditPost's built-in smart logic
            min_length = REDDIT_COLLECTION_CONFIG.get('min_selftext_length', 100)
            return post.should_fetch_comments(min_selftext_length=min_length)
        else:
            logger.warning(f"Unknown fetch_mode '{fetch_mode}', defaulting to 'smart'")
            min_length = REDDIT_COLLECTION_CONFIG.get('min_selftext_length', 100)
            return post.should_fetch_comments(min_selftext_length=min_length)

    def get_stats(self) -> dict:
        """
        Get enrichment statistics.

        Returns:
            Dictionary with enrichment stats
        """
        return self.stats.copy()
