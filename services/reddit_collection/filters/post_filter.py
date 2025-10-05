"""
Post Filter

This module handles filtering and processing of Reddit posts.
Implements filtering by score, recency, and other criteria.
"""

import logging
from typing import List
from datetime import datetime, timedelta
from ..models import RedditPost

logger = logging.getLogger(__name__)


class PostFilter:
    """Filters and processes Reddit posts based on various criteria."""

    def __init__(self):
        """Initialize the post filter."""
        pass

    def filter_by_score(self, posts: List[RedditPost], min_score: int = 0) -> List[RedditPost]:
        """
        Filter posts by minimum score.

        Args:
            posts: List of RedditPost objects
            min_score: Minimum score threshold

        Returns:
            Filtered list of posts
        """
        filtered = [post for post in posts if post.score >= min_score]
        logger.info(f"Filtered {len(posts)} posts to {len(filtered)} with score >= {min_score}")
        return filtered

    def filter_by_recency(self, posts: List[RedditPost], days: int = 7) -> List[RedditPost]:
        """
        Filter posts by recency.

        Args:
            posts: List of RedditPost objects
            days: Number of days to look back

        Returns:
            Filtered list of posts
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        filtered = [post for post in posts if post.created_utc >= cutoff]
        logger.info(f"Filtered {len(posts)} posts to {len(filtered)} from last {days} days")
        return filtered

    def filter_by_category(self, posts: List[RedditPost], categories: List[str]) -> List[RedditPost]:
        """
        Filter posts by category.

        Args:
            posts: List of RedditPost objects
            categories: List of allowed categories

        Returns:
            Filtered list of posts
        """
        filtered = [post for post in posts if post.category in categories]
        logger.info(f"Filtered {len(posts)} posts to {len(filtered)} with categories {categories}")
        return filtered

    def exclude_by_category(self, posts: List[RedditPost], excluded_categories: List[str]) -> List[RedditPost]:
        """
        Exclude posts by category.

        Args:
            posts: List of RedditPost objects
            excluded_categories: List of categories to exclude

        Returns:
            Filtered list of posts
        """
        filtered = [post for post in posts if post.category not in excluded_categories]
        logger.info(f"Filtered {len(posts)} posts to {len(filtered)} excluding {excluded_categories}")
        return filtered

    def deduplicate(self, posts: List[RedditPost]) -> List[RedditPost]:
        """
        Remove duplicate posts based on post_id.

        Args:
            posts: List of RedditPost objects

        Returns:
            Deduplicated list of posts
        """
        seen_ids = set()
        unique_posts = []

        for post in posts:
            if post.post_id not in seen_ids:
                seen_ids.add(post.post_id)
                unique_posts.append(post)

        if len(posts) != len(unique_posts):
            logger.info(f"Removed {len(posts) - len(unique_posts)} duplicate posts")

        return unique_posts

    def sort_by_score(self, posts: List[RedditPost], descending: bool = True) -> List[RedditPost]:
        """
        Sort posts by score.

        Args:
            posts: List of RedditPost objects
            descending: Sort in descending order (default: True)

        Returns:
            Sorted list of posts
        """
        sorted_posts = sorted(posts, key=lambda p: p.score, reverse=descending)
        logger.debug(f"Sorted {len(posts)} posts by score (descending={descending})")
        return sorted_posts

    def sort_by_recency(self, posts: List[RedditPost], descending: bool = True) -> List[RedditPost]:
        """
        Sort posts by creation time.

        Args:
            posts: List of RedditPost objects
            descending: Sort in descending order (default: True)

        Returns:
            Sorted list of posts
        """
        sorted_posts = sorted(posts, key=lambda p: p.created_utc, reverse=descending)
        logger.debug(f"Sorted {len(posts)} posts by recency (descending={descending})")
        return sorted_posts

    def get_top_n(self, posts: List[RedditPost], n: int) -> List[RedditPost]:
        """
        Get top N posts.

        Args:
            posts: List of RedditPost objects
            n: Number of posts to return

        Returns:
            Top N posts
        """
        return posts[:n]
