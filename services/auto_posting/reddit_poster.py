"""
Reddit Auto Poster

This module provides functionality to automatically post AI trend reports to specified subreddits.
It handles authentication, content formatting, and submission to Reddit.
"""

import os
import re
import logging
import time
from datetime import datetime
import praw
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv
import markdown
from bs4 import BeautifulSoup
import random

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reddit_posting.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RedditPoster:
    """Service for posting AI trend reports to Reddit."""
    
    def __init__(self):
        """Initialize the Reddit poster using credentials from environment variables."""
        # Get Reddit API credentials from environment variables
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        username = os.getenv('REDDIT_USERNAME')
        password = os.getenv('REDDIT_PASSWORD')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'python:reddit-ai-trends:v1.0')
        
        if not all([client_id, client_secret, username, password]):
            logger.error("Missing Reddit API credentials in environment variables")
            raise ValueError("Missing Reddit API credentials. Please check your .env file.")
        
        # Initialize PRAW Reddit instance
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            username=username,
            password=password,
            user_agent=user_agent
        )
        
        logger.info(f"Reddit poster initialized, logged in as {username}")
    
    def format_report_for_reddit(self, 
                               report_content: str, 
                               max_length: int = 40000,
                               include_source_link: bool = True,
                               source_link: str = None) -> str:
        """
        Format the report content for Reddit, ensuring it meets Reddit's formatting requirements and length limits.
        
        Args:
            report_content: The original Markdown report content
            max_length: Maximum length of the Reddit post (Reddit has a character limit)
            include_source_link: Whether to include a link to the source report
            source_link: Link to the source report
            
        Returns:
            Formatted content ready for posting to Reddit
        """
        logger.info("Formatting report for Reddit")
        
        # Remove any Reddit-incompatible formatting
        formatted_content = report_content
        
        # Extract the main sections to fit within Reddit's character limit
        if len(formatted_content) > max_length:
            logger.info(f"Report content exceeds Reddit's character limit ({len(formatted_content)} > {max_length})")
            
            # Parse the markdown to identify sections
            soup = BeautifulSoup(markdown.markdown(formatted_content), 'html.parser')
            
            # Get all headings
            headings = soup.find_all(['h1', 'h2', 'h3'])
            
            # Extract title and first few sections
            title_match = re.search(r'^# (.*?)$', formatted_content, re.MULTILINE)
            title = title_match.group(1) if title_match else "AI Trend Report"
            
            # Get introduction and today's trends section
            sections_to_include = []
            current_section = ""
            
            # First, add the title
            sections_to_include.append(f"# {title}\n\n")
            
            # Find the first section (usually Today's Trending Posts)
            first_section_match = re.search(r'^## .*?Trending Posts$(.*?)(?=^## |\Z)', 
                                           formatted_content, 
                                           re.MULTILINE | re.DOTALL)
            if first_section_match:
                sections_to_include.append(f"## Today's Trending Posts{first_section_match.group(1)}\n\n")
            
            # Get weekly trends summary
            weekly_section_match = re.search(r'^## .*?Weekly Trends$(.*?)(?=^## |\Z)',
                                           formatted_content,
                                           re.MULTILINE | re.DOTALL)
            if weekly_section_match:
                # Only include table headers and first few rows to save space
                weekly_content = weekly_section_match.group(1)
                # Get table header and first 5 rows
                table_lines = re.findall(r'\| .* \|.*$', weekly_content, re.MULTILINE)
                if len(table_lines) > 7:  # Header + separator + 5 rows
                    shortened_table = '\n'.join(table_lines[:7]) + "\n\n"
                    sections_to_include.append(f"## Weekly Trends\n\n{shortened_table}")
            
            # Add key insights section if available
            insights_section_match = re.search(r'^## .*?Key Insights$(.*?)(?=^## |\Z)',
                                             formatted_content,
                                             re.MULTILINE | re.DOTALL)
            if insights_section_match:
                sections_to_include.append(f"## Key Insights{insights_section_match.group(1)}\n\n")
            
            # Combine sections
            formatted_content = ''.join(sections_to_include)
            
            # Add truncation notice
            formatted_content += "\n\n---\n\n**Note**: This is a shortened version of the full report due to Reddit's character limits. "
        
        # Add source link if needed
        if include_source_link and source_link:
            formatted_content += f"\n\n---\n\nView the full report: [{source_link}]({source_link})"
        
        logger.info(f"Formatted report for Reddit, final length: {len(formatted_content)} characters")
        return formatted_content
    
    def create_post_title(self, report_content: str, date: Optional[str] = None) -> str:
        """
        Create an engaging title for the Reddit post based on the report content.
        
        Args:
            report_content: The report content to extract title from
            date: Optional date string to include in the title
            
        Returns:
            Title string for the Reddit post
        """
        # Try to extract the report title from the content
        title_match = re.search(r'^# (.*?)$', report_content, re.MULTILINE)
        if title_match:
            base_title = title_match.group(1)
        else:
            # If no title found, create a generic one
            base_title = "Reddit AI Trend Report"
        
        # Add date if provided, otherwise use current date
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # Add a dynamic element to make the title more engaging
        topic_patterns = [
            r'## Key Insights(.*?)(?=##|\Z)',
            r'## Today\'s Trending Posts(.*?)(?=##|\Z)',
            r'## Technical Deep Dive: (.*?)(?=\n)'
        ]
        
        engaging_elements = [
            f"🔍 See what's trending in AI today",
            f"🚀 The latest developments in AI",
            f"🤖 Today's most discussed AI topics",
            f"📊 AI trends you should know about",
            f"💡 Insights from AI communities"
        ]
        
        # Try to extract a specific topic to highlight
        highlight_topic = None
        for pattern in topic_patterns:
            match = re.search(pattern, report_content, re.DOTALL)
            if match:
                content = match.group(1)
                # Look for strong emphasis or interesting phrases
                topic_match = re.search(r'\*\*(.*?)\*\*', content)
                if topic_match:
                    highlight_topic = topic_match.group(1)
                    break
        
        # Construct the final title
        if highlight_topic and len(highlight_topic) < 50:
            title = f"{base_title} [{date}]: Featuring {highlight_topic}"
        else:
            title = f"{base_title} [{date}]: {random.choice(engaging_elements)}"
        
        # Ensure the title is not too long for Reddit
        if len(title) > 300:
            title = title[:297] + "..."
        
        logger.info(f"Created post title: {title}")
        return title
    
    def post_to_subreddit(self, 
                         subreddit_name: str, 
                         title: str, 
                         content: str, 
                         flair_id: Optional[str] = None,
                         flair_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Post the formatted report to the specified subreddit.
        
        Args:
            subreddit_name: Name of the subreddit to post to
            title: Title of the post
            content: Content to post
            flair_id: Optional flair ID to apply to the post
            flair_text: Optional flair text to apply to the post
            
        Returns:
            Dictionary containing information about the submitted post
        """
        logger.info(f"Posting to r/{subreddit_name} with title: {title}")
        
        try:
            # Get the subreddit
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Submit the post
            submission = subreddit.submit(
                title=title,
                selftext=content,
                flair_id=flair_id,
                flair_text=flair_text
            )
            
            # Log success
            logger.info(f"Successfully posted to r/{subreddit_name}, post ID: {submission.id}")
            
            # Return post information
            return {
                'post_id': submission.id,
                'title': submission.title,
                'url': submission.url,
                'permalink': submission.permalink,
                'subreddit': subreddit_name,
                'created_utc': datetime.utcfromtimestamp(submission.created_utc).isoformat(),
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error posting to r/{subreddit_name}: {e}")
            return {
                'subreddit': subreddit_name,
                'error': str(e),
                'success': False
            }
    
    def post_report(self, 
                   report_file_path: str, 
                   subreddit_name: str,
                   source_link: str = None,
                   flair_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Read a report file and post it to the specified subreddit.
        
        Args:
            report_file_path: Path to the report file
            subreddit_name: Name of the subreddit to post to
            source_link: Link to the source of the report (repository URL)
            flair_text: Optional flair text to apply to the post
            
        Returns:
            Dictionary containing information about the post attempt
        """
        logger.info(f"Posting report from {report_file_path} to r/{subreddit_name}")
        
        try:
            # Read the report file
            with open(report_file_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
            
            # Format report for Reddit
            if source_link is None:
                source_link = f"https://github.com/liyedanpdx/reddit-ai-trends/blob/main/reports/latest_report_en.md"
                
            formatted_content = self.format_report_for_reddit(
                report_content=report_content,
                include_source_link=True,
                source_link=source_link
            )
            
            # Extract date from report for title
            date_match = re.search(r'# Reddit AI Trend Report - ([\d-]+)', report_content)
            report_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
            
            # Create post title
            title = self.create_post_title(report_content, date=report_date)
            
            # Post to subreddit
            result = self.post_to_subreddit(
                subreddit_name=subreddit_name,
                title=title,
                content=formatted_content,
                flair_text=flair_text
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error in post_report: {e}")
            return {
                'subreddit': subreddit_name,
                'error': str(e),
                'success': False
            }
    
    def post_to_multiple_subreddits(self, 
                                   report_file_path: str, 
                                   subreddits: List[str],
                                   source_link: str = None,
                                   delay_between_posts: int = 600) -> List[Dict[str, Any]]:
        """
        Post a report to multiple subreddits with a delay between posts to avoid spam filters.
        
        Args:
            report_file_path: Path to the report file
            subreddits: List of subreddit names to post to
            source_link: Link to the source of the report
            delay_between_posts: Delay in seconds between posts to different subreddits
            
        Returns:
            List of dictionaries containing information about each post attempt
        """
        logger.info(f"Posting report to multiple subreddits: {', '.join(subreddits)}")
        
        results = []
        
        for i, subreddit in enumerate(subreddits):
            # Post to the subreddit
            result = self.post_report(
                report_file_path=report_file_path,
                subreddit_name=subreddit,
                source_link=source_link
            )
            
            results.append(result)
            
            # Add delay between posts (except after the last one)
            if i < len(subreddits) - 1 and result['success']:
                logger.info(f"Waiting {delay_between_posts} seconds before next post")
                time.sleep(delay_between_posts)
        
        return results


# For testing
if __name__ == "__main__":
    # Initialize the Reddit poster
    poster = RedditPoster()
    
    # Set up test parameters
    report_file = "reports/latest_report_en.md"  # Path to the latest English report
    target_subreddit = "ArtificialInteligence"   # Target subreddit for posting
    
    # Optional: Check if the report file exists
    if not os.path.exists(report_file):
        print(f"Error: Report file not found at {report_file}")
        # Try to find the latest report
        import glob
        report_files = glob.glob("reports/latest_report_*.md")
        if report_files:
            report_file = report_files[0]
            print(f"Using alternative report file: {report_file}")
        else:
            print("No report files found. Exiting.")
            exit(1)
    
    # Source link for the report
    source_link = "https://github.com/liyedanpdx/reddit-ai-trends/blob/main/reports/latest_report_en.md"
    
    print(f"Posting report from {report_file} to r/{target_subreddit}")
    
    # Post the report
    result = poster.post_report(
        report_file_path=report_file,
        subreddit_name=target_subreddit,
        source_link=source_link,
        flair_text="AI News"  # Optional flair for the post
    )
    
    # Print the result
    if result['success']:
        print(f"Successfully posted to r/{target_subreddit}")
        print(f"Post URL: {result['url']}")
        print(f"Title: {result['title']}")
    else:
        print(f"Failed to post to r/{target_subreddit}")
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    # Example of posting to multiple subreddits
    """
    multi_results = poster.post_to_multiple_subreddits(
        report_file_path=report_file,
        subreddits=["ArtificialInteligence", "MachineLearning", "LocalLLaMA"],
        source_link=source_link,
        delay_between_posts=600  # 10 minutes between posts to avoid spam filters
    )
    
    # Print results for each subreddit
    for result in multi_results:
        subreddit = result['subreddit']
        if result['success']:
            print(f"Successfully posted to r/{subreddit}: {result['url']}")
        else:
            print(f"Failed to post to r/{subreddit}: {result.get('error')}")
    """ 