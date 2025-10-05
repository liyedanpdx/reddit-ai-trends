"""
Comment Filter

This module provides filtering utilities for Reddit comments.
"""

import re
from typing import List, Dict, Any


# Bot comment patterns to filter out
BOT_COMMENT_PATTERNS = [
    r"your post is getting popular",
    r"this post has reached",
    r"i am a bot",
    r"^beep boop",
    r"this action was performed automatically",
    r"^[\*\s]*bot",
    r"contact the moderators",
    r"^automod",
    r"^automoderator",
    r"please contact the moderators",
    r"if you have any questions or concerns",
]


class CommentFilter:
    """Filter for Reddit comments."""

    @staticmethod
    def is_bot_comment(comment_body: str) -> bool:
        """
        Check if a comment is from a bot based on common patterns.

        Args:
            comment_body: The comment text

        Returns:
            True if the comment appears to be from a bot
        """
        if not comment_body:
            return True

        comment_lower = comment_body.lower().strip()

        # Check against bot patterns
        for pattern in BOT_COMMENT_PATTERNS:
            if re.search(pattern, comment_lower, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def filter_bot_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out bot comments from a list of comments.

        Args:
            comments: List of comment dictionaries

        Returns:
            Filtered list of comments without bot comments
        """
        filtered = []
        for comment in comments:
            body = comment.get('body', '')
            if not CommentFilter.is_bot_comment(body):
                filtered.append(comment)

        return filtered

    @staticmethod
    def filter_short_comments(comments: List[Dict[str, Any]], min_length: int = 20) -> List[Dict[str, Any]]:
        """
        Filter out very short comments that likely don't add value.

        Args:
            comments: List of comment dictionaries
            min_length: Minimum comment length in characters

        Returns:
            Filtered list of comments
        """
        return [c for c in comments if len(c.get('body', '')) >= min_length]
