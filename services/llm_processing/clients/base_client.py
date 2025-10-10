"""
Base LLM Client

This module provides an abstract base class for LLM clients.
All LLM provider implementations should inherit from this base class.
"""

import logging
import re
import time
import json
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from services.llm_processing.core.prompt_loader import PromptLoader
from services.reddit_collection.filters import CommentFilter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def retry_on_empty_response(max_retries: int = 3, retry_delay: int = 10):
    """
    Decorator to retry function if it returns an empty string.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        retry_delay: Delay in seconds between retries (default: 10)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> str:
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)

                    # Check if response is empty
                    if not result or len(result.strip()) == 0:
                        logger.warning(f"Received empty response (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {retry_delay} seconds...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            logger.error(f"Failed to get non-empty response after {max_retries} attempts")
                            return ""

                    return result

                except Exception as e:
                    logger.error(f"Error in {func.__name__} (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        raise

            return ""

        return wrapper
    return decorator


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    def __init__(self):
        """Initialize the base LLM client."""
        self.model = None
        self.temperature = None
        self.max_tokens = None
        self.prompt_loader = PromptLoader()
        logger.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def generate_text(self,
                     prompt: str,
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None) -> str:
        """
        Generate text using the LLM API.

        Args:
            prompt: The prompt to send to the model
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            Generated text
        """
        pass

    def _clean_response(self, text: str) -> str:
        """
        Clean LLM response by removing thinking tags and unwanted content.

        Args:
            text: Raw response text

        Returns:
            Cleaned text
        """
        # Remove <think></think> tags and their content
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Remove <thinking></thinking> tags and their content
        text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
        return text.strip()

    def _create_monthly_popular_table(self, posts: List[Dict[str, Any]], previous_report: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a markdown table of popular posts from the last month.

        Args:
            posts: List of post dictionaries
            previous_report: Optional dictionary containing previous report data for comparison

        Returns:
            Markdown table as a string
        """
        # Sort posts by score (descending)
        sorted_posts = sorted(posts, key=lambda x: x.get('score', 0), reverse=True)

        # Take top 20 posts
        top_posts = sorted_posts[:20]

        # Create table header
        table = "## Monthly Popular Posts\n\n"
        table += "| # | Title | Community | Score | Comments | Category | Posted |\n"
        table += "|---|-------|-----------|-------|----------|----------|--------|\n"

        # Add rows to table
        for i, post in enumerate(top_posts, 1):
            title = post.get('title', 'N/A')

            # Enhanced title processing to prevent Markdown formatting issues
            title = self._sanitize_title(title)

            # Get community (subreddit) information
            subreddit = post.get('subreddit', 'N/A')
            subreddit_url = f"https://www.reddit.com/r/{subreddit}"
            community_link = f"[r/{subreddit}]({subreddit_url})"

            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            category = post.get('link_flair_text', 'N/A')
            if not category or category == 'None':
                category = 'General'

            # Format the timestamp
            posted_time = self._format_timestamp(post.get('created_utc'))

            # Create post URL
            post_id = post.get('post_id', '')
            post_url = f"https://www.reddit.com/comments/{post_id}"

            # Add row to table
            table += f"| {i} | [{title}]({post_url}) | {community_link} | {score} | {comments} | {category} | {posted_time} |\n"

        return table

    def _create_weekly_popular_table(self, posts: List[Dict[str, Any]], previous_report: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a markdown table of popular posts from the last week.

        Args:
            posts: List of post dictionaries
            previous_report: Optional dictionary containing previous report data for comparison

        Returns:
            Markdown table as a string
        """
        # Sort posts by score (descending)
        sorted_posts = sorted(posts, key=lambda x: x.get('score', 0), reverse=True)

        # Take top 20 posts
        top_posts = sorted_posts[:20]

        # Create table header
        table = "## Weekly Popular Posts\n\n"
        table += "| # | Title | Community | Score | Comments | Category | Posted |\n"
        table += "|---|-------|-----------|-------|----------|----------|--------|\n"

        # Add rows to table
        for i, post in enumerate(top_posts, 1):
            title = self._sanitize_title(post.get('title', 'N/A'))

            # Get community (subreddit) information
            subreddit = post.get('subreddit', 'N/A')
            subreddit_url = f"https://www.reddit.com/r/{subreddit}"
            community_link = f"[r/{subreddit}]({subreddit_url})"

            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            category = post.get('link_flair_text', 'N/A')
            if not category or category == 'None':
                category = 'General'

            # Format the timestamp
            posted_time = self._format_timestamp(post.get('created_utc'))

            # Create post URL
            post_id = post.get('post_id', '')
            post_url = f"https://www.reddit.com/comments/{post_id}"

            # Add row to table
            table += f"| {i} | [{title}]({post_url}) | {community_link} | {score} | {comments} | {category} | {posted_time} |\n"

        return table

    def _create_trending_posts_table(self, posts: List[Dict[str, Any]]) -> str:
        """
        Create a markdown table of trending posts from the last 24 hours.

        Args:
            posts: List of post dictionaries

        Returns:
            Markdown table as a string
        """
        # Sort posts by score (descending)
        sorted_posts = sorted(posts, key=lambda x: x.get('score', 0), reverse=True)

        # Filter posts with more than 10 comments
        filtered_posts = [post for post in sorted_posts if post.get('num_comments', 0) > 10]

        # Take top 10 posts
        top_posts = filtered_posts[:10]

        # Create table header
        table = "## Trending Posts - Last 24 Hours\n\n"
        table += "| Title | Community | Score | Comments | Category | Posted |\n"
        table += "|-------|-----------|-------|----------|----------|--------|\n"

        # Add rows to table
        for post in top_posts:
            title = self._sanitize_title(post.get('title', 'N/A'))

            # Get community (subreddit) information
            subreddit = post.get('subreddit', 'N/A')
            subreddit_url = f"https://www.reddit.com/r/{subreddit}"
            community_link = f"[r/{subreddit}]({subreddit_url})"

            score = post.get('score', 0)
            comments = post.get('num_comments', 0)
            category = post.get('link_flair_text', 'N/A')
            if not category or category == 'None':
                category = 'General'

            # Format the timestamp
            posted_time = self._format_timestamp(post.get('created_utc'))

            # Create post URL
            post_id = post.get('post_id', '')
            post_url = f"https://www.reddit.com/comments/{post_id}"

            # Add row to table
            table += f"| [{title}]({post_url}) | {community_link} | {score} | {comments} | {category} | {posted_time} |\n"

        return table

    def _create_community_top_posts_tables(self, posts: List[Dict[str, Any]]) -> str:
        """
        Create tables showing top 3 posts from each community for the past week.

        Args:
            posts: List of post dictionaries

        Returns:
            Markdown tables as a string
        """
        # Filter posts from the last week (use timezone-aware datetime)
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_posts = []

        for post in posts:
            created_utc = post.get('created_utc')
            if created_utc:
                if isinstance(created_utc, str):
                    try:
                        created_utc = datetime.fromisoformat(created_utc.replace('Z', '+00:00'))
                    except ValueError:
                        continue
                elif isinstance(created_utc, datetime) and created_utc.tzinfo is None:
                    # If datetime is naive, make it timezone-aware
                    created_utc = created_utc.replace(tzinfo=timezone.utc)

                if created_utc >= week_ago:
                    weekly_posts.append(post)

        # Group posts by subreddit
        communities = {}
        for post in weekly_posts:
            subreddit = post.get('subreddit')
            if not subreddit:
                continue

            if subreddit not in communities:
                communities[subreddit] = []

            communities[subreddit].append(post)

        # Sort communities alphabetically
        sorted_communities = sorted(communities.keys())

        # Create tables for each community
        all_tables = "## Top Posts by Community\n\n"

        for community in sorted_communities:
            # Sort posts by score (descending)
            sorted_posts = sorted(communities[community], key=lambda x: x.get('score', 0), reverse=True)

            # Take top 3 posts
            top_posts = sorted_posts[:3]

            # Skip if no posts
            if not top_posts:
                continue

            # Create table header
            all_tables += f"### r/{community}\n\n"
            all_tables += "| Title | Score | Comments | Category | Posted |\n"
            all_tables += "|-------|-------|----------|----------|--------|\n"

            # Add rows to table
            for post in top_posts:
                title = self._sanitize_title(post.get('title', 'N/A'))

                score = post.get('score', 0)
                comments = post.get('num_comments', 0)
                category = post.get('link_flair_text', 'N/A')
                if not category or category == 'None':
                    category = 'General'

                # Format the timestamp
                posted_time = self._format_timestamp(post.get('created_utc'))

                # Create post URL
                post_id = post.get('post_id', '')
                post_url = f"https://www.reddit.com/comments/{post_id}"

                # Add row to table
                all_tables += f"| [{title}]({post_url}) | {score} | {comments} | {category} | {posted_time} |\n"

            # Add spacing between tables
            all_tables += "\n\n"

        return all_tables

    def _sanitize_title(self, title: str) -> str:
        """
        Sanitize title to prevent Markdown formatting issues.

        Args:
            title: Raw title string

        Returns:
            Sanitized title
        """
        # Replace pipe characters that would break table formatting
        title = title.replace('|', '&#124;')

        # Escape all brackets to prevent Markdown link interpretation
        title = title.replace('[', '\\[').replace(']', '\\]')

        # Escape quotes to prevent string interpretation issues
        title = title.replace('"', '\\"').replace("'", "\\'")

        # Replace any newline characters or carriage returns
        title = title.replace('\n', ' ').replace('\r', ' ')

        # Replace periods followed by spaces with periods and non-breaking spaces
        title = title.replace('. ', '.&nbsp;')

        # Truncate long titles
        if len(title) > 60:
            title = title[:57] + "..."

        return title

    def _format_timestamp(self, created_utc) -> str:
        """
        Format timestamp for display.

        Args:
            created_utc: Timestamp from post data

        Returns:
            Formatted timestamp string
        """
        if created_utc:
            if isinstance(created_utc, str):
                try:
                    created_utc = datetime.fromisoformat(created_utc.replace('Z', '+00:00'))
                except ValueError:
                    created_utc = datetime.utcnow()
            return created_utc.strftime("%Y-%m-%d %H:%M UTC")
        else:
            return 'N/A'

    def generate_report(self, posts: List[Dict[str, Any]], previous_report: Optional[Dict[str, Any]] = None,
                       weekly_posts: Optional[List[Dict[str, Any]]] = None,
                       monthly_posts: Optional[List[Dict[str, Any]]] = None,
                       language: str = "en",
                       reference_date: Optional[datetime] = None) -> str:
        """
        Generate a report from Reddit posts using the LLM API.

        Args:
            posts: List of post dictionaries (24-hour trending posts)
            previous_report: Previous report data for comparison
            weekly_posts: List of weekly popular posts
            monthly_posts: List of monthly popular posts
            language: Language for the report ('en' for English, 'zh' for Chinese)
            reference_date: Optional specific date to generate report for (defaults to current date)

        Returns:
            Generated report as a string
        """
        logger.info(f"Generating report from {len(posts)} posts in {language} language")

        # Use reference date or current date
        report_date = reference_date if reference_date is not None else datetime.now()
        current_date = report_date.strftime("%Y-%m-%d")

        # Create monthly popular posts table if provided
        monthly_table = ""
        if monthly_posts:
            monthly_table = self._create_monthly_popular_table(monthly_posts, previous_report)

        # Create weekly popular posts table if provided
        weekly_table = ""
        if weekly_posts:
            weekly_table = self._create_weekly_popular_table(weekly_posts, previous_report)

        # Create trending posts table
        trending_table = self._create_trending_posts_table(posts)

        # Create community top posts tables
        community_tables = self._create_community_top_posts_tables(posts)

        # Define language-specific content
        if language == "zh":
            section_headers = {
                "report_title": f"# Reddit AI 趋势报告 - {current_date}",
                "trending_posts": "## 今日热门帖子",
                "weekly_posts": "## 本周热门帖子",
                "monthly_posts": "## 本月热门帖子",
                "community_posts": "## 各社区本周热门帖子",
                "trend_analysis": "## 趋势分析"
            }
        else:
            section_headers = {
                "report_title": f"# Reddit AI Trend Report - {current_date}",
                "trending_posts": "## Today's Trending Posts",
                "weekly_posts": "## Weekly Popular Posts",
                "monthly_posts": "## Monthly Popular Posts",
                "community_posts": "## Top Posts by Community (Past Week)",
                "trend_analysis": "## Trend Analysis"
            }

        # Prepare posts with additional context (images/comments) for LLM
        # Collect from daily, weekly, and monthly posts
        all_posts_sources = [posts]
        if weekly_posts:
            all_posts_sources.append(weekly_posts)
        if monthly_posts:
            all_posts_sources.append(monthly_posts)

        posts_with_context_structured = []
        seen_post_ids = set()

        for post_source in all_posts_sources:
            for post in post_source:
                post_id = post.get('post_id')
                # Skip duplicates
                if post_id and post_id in seen_post_ids:
                    continue

                # Include posts with photo_parse, youtube_transcript_summary, web_content_summary, or comments
                has_photo = 'photo_parse' in post and post['photo_parse']
                has_youtube = 'youtube_transcript_summary' in post and post['youtube_transcript_summary']
                has_web_content = 'web_content_summary' in post and post['web_content_summary']
                has_comments = 'comments' in post and post['comments'] and len(post['comments']) > 0

                if has_photo or has_youtube or has_web_content or has_comments:
                    seen_post_ids.add(post_id)

                    # Build structured context
                    context_item = {
                        "post_id": post_id,
                        "title": post.get('title', 'N/A'),
                        "subreddit": post.get('subreddit', 'N/A'),
                        "url": post.get('url', ''),
                        "score": post.get('score', 0),
                        "num_comments": post.get('num_comments', 0)
                    }

                    # Add image description if available
                    if has_photo:
                        context_item["image_description"] = post['photo_parse']

                    # Add YouTube transcript summary if available
                    if has_youtube:
                        context_item["youtube_summary"] = post['youtube_transcript_summary']

                    # Add web content summary if available
                    if has_web_content:
                        context_item["web_content_summary"] = post['web_content_summary']

                    # Add filtered comments if available
                    if has_comments:
                        # Filter out bot comments
                        filtered_comments = CommentFilter.filter_bot_comments(post['comments'])
                        # Also filter very short comments
                        filtered_comments = CommentFilter.filter_short_comments(filtered_comments, min_length=20)

                        # Take top 3 comments by score
                        top_comments = sorted(filtered_comments, key=lambda c: c.get('score', 0), reverse=True)[:3]

                        if top_comments:
                            context_item["top_comments"] = [
                                {
                                    "author": c.get('author', 'N/A'),
                                    "score": c.get('score', 0),
                                    "body": c.get('body', '')[:300]  # Limit to 300 chars
                                }
                                for c in top_comments
                            ]

                    posts_with_context_structured.append(context_item)

        # Limit to 15 posts to avoid token overflow
        posts_with_context_structured = posts_with_context_structured[:15]
        logger.info(f"Prepared {len(posts_with_context_structured)} posts with additional context for LLM")

        # Convert to formatted JSON string for better readability in prompt
        posts_with_context_json = json.dumps(posts_with_context_structured, indent=2, ensure_ascii=False)

        # Load prompt from Jinja2 template
        prompt_context = {
            "current_date": current_date,
            "trending_table": trending_table,
            "weekly_table": weekly_table,
            "monthly_table": monthly_table,
            "community_tables": community_tables,
            "posts_with_context_json": posts_with_context_json
        }
        prompt = self.prompt_loader.get_report_prompt(language, prompt_context)

        # Log the full prompt for debugging
        logger.info(f"=" * 80)
        logger.info(f"FULL PROMPT FOR LLM ({language}):")
        logger.info(f"=" * 80)
        logger.info(prompt)
        logger.info(f"=" * 80)
        logger.info(f"Prompt length: {len(prompt)} characters")
        logger.info(f"=" * 80)

        try:
            # Generate the report using the abstract method
            report = self.generate_text(prompt)

            # Clean the response
            report = self._clean_response(report)

            # Add header and tables
            full_report = f"{section_headers['report_title']}\n\n"
            full_report += f"{section_headers['trending_posts']}\n\n"
            full_report += trending_table.replace("## Trending Posts - Last 24 Hours\n\n", "") + "\n\n"
            full_report += f"{section_headers['weekly_posts']}\n\n"
            full_report += weekly_table.replace("## Weekly Popular Posts\n\n", "") + "\n\n"
            full_report += f"{section_headers['monthly_posts']}\n\n"
            full_report += monthly_table.replace("## Monthly Popular Posts\n\n", "") + "\n\n"
            full_report += f"{section_headers['community_posts']}\n\n"
            full_report += community_tables.replace("## Top Posts by Community\n\n", "") + "\n\n"
            full_report += f"{section_headers['trend_analysis']}\n\n"
            full_report += report

            return full_report
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error generating report: {e}"

    def generate_multilingual_reports(self, posts: List[Dict[str, Any]], previous_data: Optional[Dict[str, Any]] = None,
                                     weekly_posts: Optional[List[Dict[str, Any]]] = None,
                                     monthly_posts: Optional[List[Dict[str, Any]]] = None,
                                     languages: List[str] = ["en", "zh"],
                                     reference_date: Optional[datetime] = None) -> Dict[str, str]:
        """
        Generate reports in multiple languages.

        Args:
            posts: List of post dictionaries (24-hour trending posts)
            previous_data: Optional dictionary containing previous report data for comparison
            weekly_posts: List of weekly popular posts
            monthly_posts: List of monthly popular posts
            languages: List of language codes to generate reports for
            reference_date: Optional specific date to generate report for (defaults to current date)

        Returns:
            Dictionary mapping language codes to generated reports
        """
        reports = {}

        for lang in languages:
            logger.info(f"Generating report in {lang} language")
            report = self.generate_report(posts, previous_data, weekly_posts, monthly_posts, language=lang, reference_date=reference_date)
            reports[lang] = report

        return reports
