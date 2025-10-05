"""
Comment Fetcher

This module handles fetching comments from Reddit posts.
Responsible for retrieving top comments sorted by score.
"""

import logging
from typing import List, Dict, Any
from ..models import RedditComment
from ..client import RedditClient

logger = logging.getLogger(__name__)


class CommentFetcher:
    """Handles fetching comments from Reddit posts."""

    def __init__(self, client: RedditClient):
        """
        Initialize the comment fetcher.

        Args:
            client: RedditClient instance
        """
        self.client = client

    def fetch_top_comments(self, post_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch top comments for a post sorted by score.

        Args:
            post_id: Reddit post ID
            limit: Maximum number of comments to return

        Returns:
            List of comment dictionaries sorted by score (descending)
        """
        logger.info(f"Fetching top {limit} comments for post {post_id}")

        try:
            # Get the submission
            submission = self.client.get_submission(post_id)

            # IMPORTANT: Set comment_sort BEFORE accessing any post attributes
            # This must happen before PRAW lazy-loads the comments
            submission.comment_sort = "top"

            # Replace more comments (limit=0 means don't expand "load more")
            submission.comments.replace_more(limit=0)

            # Get top comments (already sorted by score due to comment_sort="top")
            comments = []
            for comment in list(submission.comments)[:limit]:
                # Convert PRAW comment to RedditComment
                reddit_comment = RedditComment.from_praw(comment)
                # Convert to dict for compatibility with existing code
                comments.append(reddit_comment.to_dict())

            logger.info(f"Successfully fetched {len(comments)} comments for post {post_id}")
            return comments

        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []

    def fetch_comments_for_posts(
        self,
        post_ids: List[str],
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch top comments for multiple posts.

        Args:
            post_ids: List of Reddit post IDs
            limit: Maximum number of comments per post

        Returns:
            Dictionary mapping post_id to list of comments
        """
        logger.info(f"Fetching comments for {len(post_ids)} posts")

        comments_by_post = {}
        for post_id in post_ids:
            comments = self.fetch_top_comments(post_id, limit)
            comments_by_post[post_id] = comments

        logger.info(f"Successfully fetched comments for {len(comments_by_post)} posts")
        return comments_by_post
