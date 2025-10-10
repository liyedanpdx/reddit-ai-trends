"""
Reddit Data Collector

This module provides a unified interface for collecting Reddit data.
Uses Clean Architecture with separate layers for fetching, enriching, and filtering.
"""

import logging
from typing import List, Dict, Any, Optional

from .client import RedditClient
from .models import RedditPost
from .fetchers import PostFetcher, CommentFetcher
from .enrichers import ImageEnricher, CommentEnricher, YouTubeEnricher, WebContentEnricher
from .filters import PostFilter
from services.image_analyzer import get_image_analyzer
from database.mongodb import MongoDBClient
from config import (
    REDDIT_COLLECTION_CONFIG,
    EXCLUDED_CATEGORIES,
    YOUTUBE_ANALYSIS_CONFIG,
    WEB_CONTENT_ANALYSIS_CONFIG,
    LLM_PROVIDERS,
    CURRENT_LLM_PROVIDER
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RedditDataCollector:
    """Service for collecting and storing Reddit data with Clean Architecture."""

    def __init__(self, db_client: Optional[MongoDBClient] = None):
        """
        Initialize the Reddit data collector.

        Args:
            db_client: MongoDB client for storing data (optional)
        """
        # Layer 1: Client
        self.client = RedditClient()

        # Layer 2: Fetchers
        self.post_fetcher = PostFetcher(self.client)
        self.comment_fetcher = CommentFetcher(self.client)

        # Layer 3: Enrichers
        image_analyzer = get_image_analyzer()
        self.image_enricher = ImageEnricher(image_analyzer, db_client)
        self.comment_enricher = CommentEnricher(self.comment_fetcher)

        # Initialize YouTube enricher
        openrouter_api_key = LLM_PROVIDERS.get(CURRENT_LLM_PROVIDER, {}).get("api_key", "")
        self.youtube_enricher = YouTubeEnricher(
            api_key=openrouter_api_key,
            model=YOUTUBE_ANALYSIS_CONFIG.get("model", "deepseek/deepseek-chat-v3.1:free"),
            max_tokens=YOUTUBE_ANALYSIS_CONFIG.get("max_tokens", 500),
            enabled=YOUTUBE_ANALYSIS_CONFIG.get("enabled", True)
        )

        # Initialize Web content enricher
        self.web_content_enricher = WebContentEnricher(
            firecrawl_api_key=WEB_CONTENT_ANALYSIS_CONFIG.get("firecrawl_api_key", ""),
            openrouter_api_key=openrouter_api_key,
            model=WEB_CONTENT_ANALYSIS_CONFIG.get("model", "deepseek/deepseek-chat-v3.1:free"),
            max_tokens=WEB_CONTENT_ANALYSIS_CONFIG.get("max_tokens", 500),
            enabled=WEB_CONTENT_ANALYSIS_CONFIG.get("enabled", True)
        )

        # Layer 3: Filters
        self.post_filter = PostFilter()

        # Database client
        self.db_client = db_client

        logger.info("Reddit data collector initialized with Clean Architecture")
        if EXCLUDED_CATEGORIES:
            logger.info(f"Excluding posts with categories: {', '.join(EXCLUDED_CATEGORIES)}")

    def get_detailed_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 100,
        time_filter: str = "week",
        fetch_comments: Optional[str] = None,
        top_comments: Optional[int] = None,
        analyze_images: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get detailed posts from a subreddit with optional comments and image analysis.
        Uses database caching to minimize API calls.

        Args:
            subreddit: Name of the subreddit
            limit: Maximum number of posts to return
            time_filter: Time filter for posts (hour, day, week, month, year, all)
            fetch_comments: Comment fetch mode - "true", "false", or "smart" (default: from config)
            top_comments: Number of top comments to fetch (default: from config)
            analyze_images: Whether to analyze images (default: from config)

        Returns:
            List of detailed post dictionaries with comments and photo_parse if enabled
        """
        # Use config defaults if not specified
        if fetch_comments is None:
            fetch_comments = REDDIT_COLLECTION_CONFIG['fetch_comments']
        if top_comments is None:
            top_comments = REDDIT_COLLECTION_CONFIG['top_comments_limit']
        if analyze_images is None:
            analyze_images = REDDIT_COLLECTION_CONFIG['analyze_images']

        logger.info(
            f"Getting detailed posts from r/{subreddit} "
            f"(limit: {limit}, comments: {fetch_comments}, images: {analyze_images})"
        )

        # Step 1: Fetch posts
        posts = self.post_fetcher.fetch_top_posts(subreddit, time_filter, limit)

        if not posts:
            logger.warning(f"No posts found in r/{subreddit}")
            return []

        # Track statistics
        stats = {
            "total": len(posts),
            "image_analyzed": 0,
            "image_cached": 0,
            "comments_fetched": 0,
            "comments_skipped": 0
        }

        # Step 2: Process each post
        detailed_posts = []
        for post in posts:
            # Check database for existing data
            existing_post = None
            if self.db_client:
                existing_post = self.db_client.get_post_by_id(post.post_id)

            # Step 3: Enrich with image analysis (if enabled)
            if analyze_images:
                post = self.image_enricher.enrich_post(post, existing_post)

            # Step 4: Enrich with YouTube transcript (if enabled via config)
            post = self.youtube_enricher.enrich_post(post, existing_post)

            # Step 5: Enrich with web content (if enabled via config)
            post = self.web_content_enricher.enrich_post(post, existing_post)

            # Step 6: Enrich with comments (based on mode)
            post = self.comment_enricher.enrich_post(post, fetch_comments, top_comments)

            detailed_posts.append(post)

        # Collect stats from enrichers
        image_stats = self.image_enricher.get_stats()
        comment_stats = self.comment_enricher.get_stats()

        stats["image_analyzed"] = image_stats.get("analyzed", 0)
        stats["image_cached"] = image_stats.get("cached", 0)
        stats["comments_fetched"] = comment_stats.get("fetched", 0)
        stats["comments_skipped"] = comment_stats.get("skipped", 0)

        # Convert RedditPost objects to dictionaries
        detailed_dicts = [post.to_dict() for post in detailed_posts]

        logger.info(f"Got {len(detailed_dicts)} detailed posts from r/{subreddit} - Stats: {stats}")
        return detailed_dicts

    def get_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 100,
        time_filter: str = "week"
    ) -> List[Dict[str, Any]]:
        """
        Get basic posts from a subreddit (without enrichments).

        Args:
            subreddit: Name of the subreddit
            limit: Maximum number of posts to return
            time_filter: Time filter for posts (hour, day, week, month, year, all)

        Returns:
            List of post dictionaries
        """
        logger.info(f"Getting posts from r/{subreddit} (limit: {limit}, time_filter: {time_filter})")

        posts = self.post_fetcher.fetch_top_posts(subreddit, time_filter, limit)
        post_dicts = [post.to_dict() for post in posts]

        logger.info(f"Got {len(post_dicts)} posts from r/{subreddit}")
        return post_dicts

    def get_weekly_popular_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get the most popular posts from the last week across multiple subreddits.

        Args:
            subreddits: List of subreddits to collect from (defaults to config)
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries
        """
        logger.info(f"Getting weekly popular posts (limit: {limit})")

        # Use default subreddits if not provided
        if not subreddits:
            subreddits = REDDIT_COLLECTION_CONFIG['subreddits']

        all_posts = []
        for subreddit in subreddits:
            posts = self.post_fetcher.fetch_top_posts(subreddit, "week", limit)
            all_posts.extend(posts)

        # Sort by score and get top N
        sorted_posts = self.post_filter.sort_by_score(all_posts)
        top_posts = self.post_filter.get_top_n(sorted_posts, limit)

        top_dicts = [post.to_dict() for post in top_posts]
        logger.info(f"Got {len(top_dicts)} weekly popular posts")
        return top_dicts

    def get_monthly_popular_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get the most popular posts from the last month across multiple subreddits.

        Args:
            subreddits: List of subreddits to collect from (defaults to config)
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries
        """
        logger.info(f"Getting monthly popular posts (limit: {limit})")

        # Use default subreddits if not provided
        if not subreddits:
            subreddits = REDDIT_COLLECTION_CONFIG['subreddits']

        all_posts = []
        for subreddit in subreddits:
            posts = self.post_fetcher.fetch_top_posts(subreddit, "month", limit)
            all_posts.extend(posts)

        # Sort by score and get top N
        sorted_posts = self.post_filter.sort_by_score(all_posts)
        top_posts = self.post_filter.get_top_n(sorted_posts, limit)

        top_dicts = [post.to_dict() for post in top_posts]
        logger.info(f"Got {len(top_dicts)} monthly popular posts")
        return top_dicts

    def filter_posts_by_category(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out posts with excluded categories.

        Args:
            posts: List of post dictionaries

        Returns:
            Filtered list of posts
        """
        if not EXCLUDED_CATEGORIES:
            return posts

        filtered_posts = []
        for post in posts:
            category = post.get('category')
            if category and category in EXCLUDED_CATEGORIES:
                logger.info(f"Excluding post with category '{category}': {post.get('title', 'No title')}")
                continue
            filtered_posts.append(post)

        logger.info(f"Filtered {len(posts)} posts to {len(filtered_posts)} (excluded {len(posts) - len(filtered_posts)})")
        return filtered_posts
