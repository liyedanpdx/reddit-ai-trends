"""
Reddit Post Detail Fetch Service

This module provides functionality to fetch detailed information about Reddit posts,
including comments and additional metadata.
"""

import os
import praw
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from config import POST_CATEGORIES
from services.image_analyzer import get_image_analyzer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditPostDetailFetcher:
    """Service for fetching detailed information about Reddit posts."""

    def __init__(self, db_client=None):
        """Initialize the Reddit post detail fetcher using credentials from environment variables."""
        # Get Reddit API credentials from environment variables
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT')

        if not all([client_id, client_secret, user_agent]):
            raise ValueError("Reddit API credentials not found in environment variables")

        # Initialize PRAW Reddit instance
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )

        # Initialize image analyzer
        self.image_analyzer = get_image_analyzer()

        # Store database client reference
        self.db_client = db_client

        logger.info("Reddit post detail fetcher initialized")
    
    def get_post_details(self, post_id: str, existing_post: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific post.

        Args:
            post_id: ID of the post
            existing_post: Optional existing post data from database (to avoid duplicate queries)

        Returns:
            Dictionary containing post details, or None if post not found
        """
        logger.info(f"Fetching details for post {post_id}")

        try:
            # Get post instance
            post = self.reddit.submission(id=post_id)

            # IMPORTANT: Set comment_sort BEFORE accessing any post attributes
            # This must happen before PRAW lazy-loads the comments
            post.comment_sort = "top"

            # Extract post data (pass existing_post to avoid duplicate DB query)
            post_data = self._convert_post_to_dict(post, existing_post=existing_post)

            # Get comments (comment_sort already set above)
            post_data['comments'] = self._get_post_comments(post)

            logger.info(f"Successfully fetched details for post {post_id}")
            return post_data

        except Exception as e:
            import traceback
            logger.error(f"Error fetching details for post {post_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _convert_post_to_dict(self, post, existing_post: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Convert a PRAW post object to a dictionary.

        Args:
            post: PRAW post object
            existing_post: Optional existing post data from database (to avoid duplicate queries)

        Returns:
            Post dictionary
        """
        # Convert created timestamp to datetime
        created_utc = datetime.fromtimestamp(post.created_utc)

        # Determine post category
        category = self._determine_post_category(post)

        # Extract post data
        post_data = {
            "post_id": post.id,
            "title": post.title,
            "author": str(post.author) if post.author else "[deleted]",
            "created_utc": created_utc,
            "score": post.score,
            "upvote_ratio": post.upvote_ratio,
            "num_comments": post.num_comments,
            "permalink": f"https://www.reddit.com{post.permalink}",
            "url": post.url,
            "is_self": post.is_self,
            "selftext": post.selftext if post.is_self else "",
            "subreddit": post.subreddit.display_name,
            "link_flair_text": post.link_flair_text,
            "category": category
        }

        # Analyze image if URL is an image (check by file extension)
        # Only analyze if not already in database
        should_analyze_image = False
        if self.image_analyzer.enabled and self.image_analyzer.is_image_url(post.url):
            # Use provided existing_post if available, otherwise query database
            if existing_post is None and self.db_client:
                existing_post = self.db_client.get_post_by_id(post.id)

            if existing_post and "photo_parse" in existing_post:
                # Use existing photo_parse
                post_data["photo_parse"] = existing_post["photo_parse"]
                logger.info(f"Using existing photo_parse for post {post.id}")
            else:
                # Need to analyze
                should_analyze_image = True

        if should_analyze_image:
            photo_description = self.image_analyzer.analyze_image(post.url)
            if photo_description:
                post_data["photo_parse"] = photo_description
                logger.info(f"Added new photo_parse for post {post.id}")

        return post_data
    
    def _get_post_comments(self, post, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top comments for a specific post sorted by score.

        Note: comment_sort must be set BEFORE calling this method (done in get_post_details)

        Args:
            post: PRAW post object (with comment_sort already set to "top")
            limit: Maximum number of comments to return

        Returns:
            List of comment dictionaries sorted by score (descending)
        """
        # Replace more comments (limit=0 means don't expand "load more")
        post.comments.replace_more(limit=0)

        # Get top comments (already sorted by score due to comment_sort="top" set earlier)
        comments = []
        for comment in list(post.comments)[:limit]:
            comment_data = self._convert_comment_to_dict(comment)
            comments.append(comment_data)

        return comments
    
    def _convert_comment_to_dict(self, comment) -> Dict[str, Any]:
        """
        Convert a PRAW comment object to a dictionary.
        
        Args:
            comment: PRAW comment object
            
        Returns:
            Comment dictionary
        """
        # Convert created timestamp to datetime
        created_utc = datetime.fromtimestamp(comment.created_utc)
        
        # Extract comment data
        comment_data = {
            "comment_id": comment.id,
            "author": str(comment.author) if comment.author else "[deleted]",
            "created_utc": created_utc,
            "score": comment.score,
            "body": comment.body
        }
        
        return comment_data
    
    def _determine_post_category(self, post) -> str:
        """
        Determine the category of a post based on its flair.

        Args:
            post: PRAW post object

        Returns:
            Category string (flair text or 'general')
        """
        # Use flair text as category if available
        if post.link_flair_text:
            return post.link_flair_text

        # Default category
        return "general"
    
    def get_multiple_post_details(self, post_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get detailed information about multiple posts.
        
        Args:
            post_ids: List of post IDs
            
        Returns:
            List of post detail dictionaries
        """
        logger.info(f"Fetching details for {len(post_ids)} posts")
        
        post_details = []
        for post_id in post_ids:
            post_data = self.get_post_details(post_id)
            if post_data:
                post_details.append(post_data)
        
        logger.info(f"Successfully fetched details for {len(post_details)} posts")
        return post_details 