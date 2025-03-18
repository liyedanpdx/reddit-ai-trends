"""
Reddit User Information Fetcher

This module provides functionality to fetch detailed information about Reddit users,
including their post history, comment history, and contribution statistics.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import praw
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditUserFetcher:
    """Service for fetching Reddit user information."""
    
    def __init__(self):
        """Initialize the Reddit user fetcher using credentials from environment variables."""
        # Get Reddit API credentials from environment variables
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT', 'python:reddit-ai-trends:v1.0')
        
        if not client_id or not client_secret:
            logger.warning("Reddit API credentials not found in environment variables")
        
        # Initialize PRAW Reddit instance
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )
        
        logger.info("Reddit user fetcher initialized")
    
    def get_user_profile(self, username: str) -> Dict[str, Any]:
        """
        Get basic profile information for a Reddit user.
        
        Args:
            username: Username of the Reddit user
            
        Returns:
            Dictionary containing user profile information
        """
        logger.info(f"Fetching profile for user: {username}")
        
        try:
            # Get the Redditor object
            user = self.reddit.redditor(username)
            
            # Build the profile data
            profile = {
                'username': username,
                'created_utc': datetime.fromtimestamp(user.created_utc).isoformat(),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'is_gold': user.is_gold,
                'is_mod': user.is_mod,
                'has_verified_email': user.has_verified_email if hasattr(user, 'has_verified_email') else None,
                'subreddit': {
                    'display_name': f"u_{username}",
                    'title': user.subreddit.title if hasattr(user, 'subreddit') else None,
                    'description': user.subreddit.description if hasattr(user, 'subreddit') else None,
                },
                'fetch_time': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully fetched profile for user: {username}")
            return profile
        
        except Exception as e:
            logger.error(f"Error fetching profile for user {username}: {e}")
            return {
                'username': username,
                'error': str(e),
                'fetch_time': datetime.now().isoformat()
            }
    
    def get_user_trophies(self, username: str) -> List[Dict[str, Any]]:
        """
        Get trophies and awards earned by a Reddit user.
        
        Args:
            username: Username of the Reddit user
            
        Returns:
            List of dictionaries containing trophy information
        """
        logger.info(f"Fetching trophies for user: {username}")
        
        try:
            # Get the Redditor object
            user = self.reddit.redditor(username)
            
            # Get trophies
            trophies = []
            
            for trophy in user.trophies():
                trophy_data = {
                    'name': trophy.name,
                    'description': trophy.description if hasattr(trophy, 'description') else None,
                    'award_id': trophy.award_id if hasattr(trophy, 'award_id') else None,
                    'icon_70': trophy.icon_70 if hasattr(trophy, 'icon_70') else None,
                    'granted_at': datetime.fromtimestamp(trophy.granted_utc).isoformat() if hasattr(trophy, 'granted_utc') and trophy.granted_utc else None
                }
                trophies.append(trophy_data)
            
            logger.info(f"Successfully fetched {len(trophies)} trophies for user: {username}")
            return trophies
        
        except Exception as e:
            logger.error(f"Error fetching trophies for user {username}: {e}")
            return []
    
    def get_user_submissions(self, username: str, limit: int = 50, time_filter: str = "year") -> List[Dict[str, Any]]:
        """
        Get submissions (posts) made by a Reddit user.
        
        Args:
            username: Username of the Reddit user
            limit: Maximum number of submissions to retrieve
            time_filter: Time filter for submissions ('all', 'day', 'month', 'week', 'year')
            
        Returns:
            List of dictionaries containing submission information
        """
        logger.info(f"Fetching submissions for user: {username}, limit: {limit}, time_filter: {time_filter}")
        
        try:
            # Get the Redditor object
            user = self.reddit.redditor(username)
            
            # Get submissions
            submissions = []
            
            # Different methods based on time filter
            if time_filter == "all":
                posts = user.submissions.new(limit=limit)
            else:
                posts = user.submissions.top(time_filter=time_filter, limit=limit)
            
            for post in posts:
                submission = {
                    'post_id': post.id,
                    'title': post.title,
                    'subreddit': post.subreddit.display_name,
                    'created_utc': datetime.fromtimestamp(post.created_utc).isoformat(),
                    'score': post.score,
                    'upvote_ratio': post.upvote_ratio,
                    'num_comments': post.num_comments,
                    'permalink': post.permalink,
                    'url': post.url,
                    'is_self': post.is_self,
                    'selftext': post.selftext if post.is_self else "",
                    'is_video': post.is_video,
                    'post_hint': post.post_hint if hasattr(post, 'post_hint') else None,
                    'domain': post.domain,
                    'link_flair_text': post.link_flair_text
                }
                submissions.append(submission)
            
            logger.info(f"Successfully fetched {len(submissions)} submissions for user: {username}")
            return submissions
        
        except Exception as e:
            logger.error(f"Error fetching submissions for user {username}: {e}")
            return []
    
    def get_user_comments(self, username: str, limit: int = 50, time_filter: str = "month") -> List[Dict[str, Any]]:
        """
        Get comments made by a Reddit user.
        
        Args:
            username: Username of the Reddit user
            limit: Maximum number of comments to retrieve
            time_filter: Time filter for comments ('all', 'day', 'month', 'week', 'year')
            
        Returns:
            List of dictionaries containing comment information
        """
        logger.info(f"Fetching comments for user: {username}, limit: {limit}, time_filter: {time_filter}")
        
        try:
            # Get the Redditor object
            user = self.reddit.redditor(username)
            
            # Get comments
            comments = []
            
            # Different methods based on time filter
            if time_filter == "all":
                user_comments = user.comments.new(limit=limit)
            else:
                user_comments = user.comments.top(time_filter=time_filter, limit=limit)
            
            for comment in user_comments:
                comment_data = {
                    'comment_id': comment.id,
                    'subreddit': comment.subreddit.display_name,
                    'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat(),
                    'score': comment.score,
                    'body': comment.body,
                    'permalink': comment.permalink,
                    'submission_id': comment.submission.id,
                    'submission_title': comment.submission.title,
                    'is_submitter': comment.is_submitter,
                    'distinguished': comment.distinguished
                }
                comments.append(comment_data)
            
            logger.info(f"Successfully fetched {len(comments)} comments for user: {username}")
            return comments
        
        except Exception as e:
            logger.error(f"Error fetching comments for user {username}: {e}")
            return []
    
    def analyze_user_contributions(self, username: str, time_period_days: int = 90) -> Dict[str, Any]:
        """
        Analyze a user's contributions to provide insights about their expertise and activity.
        
        Args:
            username: Username of the Reddit user
            time_period_days: Number of days to analyze
            
        Returns:
            Dictionary containing analysis of user contributions
        """
        logger.info(f"Analyzing contributions for user: {username} over past {time_period_days} days")
        
        try:
            # Get basic profile
            profile = self.get_user_profile(username)
            
            # Get recent submissions and comments
            submissions = self.get_user_submissions(username, limit=100, time_filter="year")
            comments = self.get_user_comments(username, limit=200, time_filter="year")
            
            # Filter by time period
            cutoff_date = datetime.now() - timedelta(days=time_period_days)
            recent_submissions = [
                s for s in submissions 
                if datetime.fromisoformat(s['created_utc']) > cutoff_date
            ]
            recent_comments = [
                c for c in comments 
                if datetime.fromisoformat(c['created_utc']) > cutoff_date
            ]
            
            # Analyze subreddit distribution
            subreddit_activity = {}
            for submission in recent_submissions:
                subreddit = submission['subreddit']
                if subreddit not in subreddit_activity:
                    subreddit_activity[subreddit] = {'submissions': 0, 'comments': 0, 'karma': 0}
                subreddit_activity[subreddit]['submissions'] += 1
                subreddit_activity[subreddit]['karma'] += submission['score']
            
            for comment in recent_comments:
                subreddit = comment['subreddit']
                if subreddit not in subreddit_activity:
                    subreddit_activity[subreddit] = {'submissions': 0, 'comments': 0, 'karma': 0}
                subreddit_activity[subreddit]['comments'] += 1
                subreddit_activity[subreddit]['karma'] += comment['score']
            
            # Calculate top subreddits by activity
            top_subreddits = sorted(
                [(k, v) for k, v in subreddit_activity.items()],
                key=lambda x: x[1]['submissions'] + x[1]['comments'],
                reverse=True
            )
            
            # Calculate highest karma content
            top_submissions = sorted(recent_submissions, key=lambda x: x['score'], reverse=True)[:5]
            top_comments = sorted(recent_comments, key=lambda x: x['score'], reverse=True)[:5]
            
            # Identify potential areas of expertise based on where they post/comment most
            expertise_areas = [
                subreddit for subreddit, activity in top_subreddits[:5]
                if activity['submissions'] + activity['comments'] > 3  # At least 3 contributions
            ]
            
            # Put everything together
            analysis = {
                'username': username,
                'profile': profile,
                'analysis_period_days': time_period_days,
                'activity_summary': {
                    'total_submissions': len(recent_submissions),
                    'total_comments': len(recent_comments),
                    'submission_karma': sum(s['score'] for s in recent_submissions),
                    'comment_karma': sum(c['score'] for c in recent_comments),
                    'active_subreddits': len(subreddit_activity),
                    'posting_frequency': len(recent_submissions) / time_period_days if time_period_days > 0 else 0,
                    'commenting_frequency': len(recent_comments) / time_period_days if time_period_days > 0 else 0,
                },
                'top_subreddits': [
                    {
                        'subreddit': subreddit,
                        'submissions': activity['submissions'],
                        'comments': activity['comments'],
                        'karma': activity['karma']
                    }
                    for subreddit, activity in top_subreddits[:10]  # Top 10 subreddits
                ],
                'top_content': {
                    'submissions': [
                        {
                            'title': s['title'],
                            'url': f"https://www.reddit.com{s['permalink']}",
                            'score': s['score'],
                            'subreddit': s['subreddit'],
                            'created_utc': s['created_utc']
                        }
                        for s in top_submissions
                    ],
                    'comments': [
                        {
                            'body': c['body'][:300] + ('...' if len(c['body']) > 300 else ''),
                            'url': f"https://www.reddit.com{c['permalink']}",
                            'score': c['score'],
                            'subreddit': c['subreddit'],
                            'created_utc': c['created_utc']
                        }
                        for c in top_comments
                    ]
                },
                'potential_expertise': expertise_areas,
                'analysis_time': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully analyzed contributions for user: {username}")
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing contributions for user {username}: {e}")
            return {
                'username': username,
                'error': str(e),
                'analysis_time': datetime.now().isoformat()
            }
    
    def analyze_user_expertise_with_trophies(self, username: str, time_period_days: int = 90) -> Dict[str, Any]:
        """
        Analyze a user's expertise including their trophies and awards.
        
        Args:
            username: Username of the Reddit user
            time_period_days: Number of days to analyze activity for
            
        Returns:
            Dictionary containing comprehensive expertise analysis
        """
        logger.info(f"Analyzing expertise with trophies for user: {username}")
        
        try:
            # Get basic contribution analysis
            contribution_analysis = self.analyze_user_contributions(username, time_period_days)
            
            # Get user trophies
            trophies = self.get_user_trophies(username)
            
            # Map trophies to expertise areas
            expertise_trophies = []
            for trophy in trophies:
                trophy_name = trophy.get('name', '').lower()
                trophy_relevance = None
                
                # Analyze trophy relevance to expertise
                if any(term in trophy_name for term in ['gilding', 'gold', 'platinum', 'award']):
                    trophy_relevance = 'Community Recognition'
                elif any(term in trophy_name for term in ['best', 'top', 'excellent']):
                    trophy_relevance = 'Quality Contribution'
                elif 'verified' in trophy_name:
                    trophy_relevance = 'Identity Verification'
                elif any(term in trophy_name for term in ['mod', 'moderator']):
                    trophy_relevance = 'Community Leadership'
                elif any(term in trophy_name for term in ['year', 'veteran']):
                    trophy_relevance = 'Experience'
                
                if trophy_relevance:
                    expertise_trophies.append({
                        'trophy': trophy,
                        'relevance': trophy_relevance
                    })
            
            # Calculate expertise score components
            contribution_score = 0
            if contribution_analysis.get('activity_summary'):
                # Base on karma and frequency
                summary = contribution_analysis['activity_summary']
                contribution_score = (
                    summary.get('submission_karma', 0) * 0.3 + 
                    summary.get('comment_karma', 0) * 0.3 +
                    summary.get('posting_frequency', 0) * 20 +
                    summary.get('commenting_frequency', 0) * 10
                ) / 100
            
            # Trophy score based on number and relevance
            trophy_score = len(trophies) * 5
            trophy_score += len([t for t in expertise_trophies if t['relevance'] in 
                              ['Quality Contribution', 'Community Leadership']]) * 10
            
            # Combined expertise score
            total_score = min(100, contribution_score + trophy_score)
            
            # Create final expertise analysis
            expertise_analysis = {
                'username': username,
                'profile': contribution_analysis.get('profile', {}),
                'expertise_score': round(total_score, 2),
                'contribution_stats': contribution_analysis.get('activity_summary', {}),
                'expertise_areas': contribution_analysis.get('potential_expertise', []),
                'trophies': trophies,
                'trophy_count': len(trophies),
                'expertise_trophies': expertise_trophies,
                'expertise_ranking': self._get_expertise_ranking(total_score),
                'analysis_time': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully analyzed expertise with trophies for user: {username}")
            return expertise_analysis
        
        except Exception as e:
            logger.error(f"Error analyzing expertise with trophies for user {username}: {e}")
            return {
                'username': username,
                'error': str(e),
                'analysis_time': datetime.now().isoformat()
            }
    
    def _get_expertise_ranking(self, score: float) -> str:
        """
        Convert numeric score to expertise ranking label.
        
        Args:
            score: Numeric expertise score (0-100)
            
        Returns:
            String ranking label
        """
        if score >= 80:
            return "Expert"
        elif score >= 60:
            return "Authority"
        elif score >= 40:
            return "Contributor"
        elif score >= 20:
            return "Active Participant"
        else:
            return "Casual User"
    
    def find_most_valuable_contributors(self, subreddit: str, time_filter: str = "month", limit: int = 25) -> List[Dict[str, Any]]:
        """
        Find the most valuable contributors in a subreddit based on post and comment karma.
        
        Args:
            subreddit: Name of the subreddit
            time_filter: Time filter ('day', 'week', 'month', 'year', 'all')
            limit: Maximum number of contributors to return
            
        Returns:
            List of dictionaries containing contributor information
        """
        logger.info(f"Finding most valuable contributors in r/{subreddit}, time_filter: {time_filter}")
        
        try:
            # Get top posts
            sub = self.reddit.subreddit(subreddit)
            
            # Track users we've seen
            user_contributions = {}
            
            # Get top posts
            for post in sub.top(time_filter=time_filter, limit=limit):
                username = post.author.name if post.author else "[deleted]"
                
                if username != "[deleted]":
                    if username not in user_contributions:
                        user_contributions[username] = {
                            'username': username,
                            'post_karma': 0,
                            'comment_karma': 0,
                            'post_count': 0,
                            'comment_count': 0,
                            'top_posts': [],
                            'top_comments': []
                        }
                    
                    # Update post stats
                    user_contributions[username]['post_karma'] += post.score
                    user_contributions[username]['post_count'] += 1
                    
                    # Add to top posts if needed
                    if len(user_contributions[username]['top_posts']) < 3:
                        user_contributions[username]['top_posts'].append({
                            'title': post.title,
                            'url': f"https://www.reddit.com{post.permalink}",
                            'score': post.score,
                            'created_utc': datetime.fromtimestamp(post.created_utc).isoformat()
                        })
                    
                    # Get comments
                    post.comments.replace_more(limit=0)  # Avoid loading MoreComments
                    for comment in post.comments[:10]:  # Look at top comments
                        commenter = comment.author.name if comment.author else "[deleted]"
                        
                        if commenter != "[deleted]":
                            if commenter not in user_contributions:
                                user_contributions[commenter] = {
                                    'username': commenter,
                                    'post_karma': 0,
                                    'comment_karma': 0,
                                    'post_count': 0,
                                    'comment_count': 0,
                                    'top_posts': [],
                                    'top_comments': []
                                }
                            
                            # Update comment stats
                            user_contributions[commenter]['comment_karma'] += comment.score
                            user_contributions[commenter]['comment_count'] += 1
                            
                            # Add to top comments if needed
                            if len(user_contributions[commenter]['top_comments']) < 3:
                                user_contributions[commenter]['top_comments'].append({
                                    'body': comment.body[:200] + ('...' if len(comment.body) > 200 else ''),
                                    'url': f"https://www.reddit.com{comment.permalink}",
                                    'score': comment.score,
                                    'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat()
                                })
            
            # Convert to list and calculate total karma
            contributors = []
            for username, data in user_contributions.items():
                data['total_karma'] = data['post_karma'] + data['comment_karma']
                data['total_contributions'] = data['post_count'] + data['comment_count']
                contributors.append(data)
            
            # Sort by total karma
            contributors.sort(key=lambda x: x['total_karma'], reverse=True)
            
            logger.info(f"Found {len(contributors)} contributors in r/{subreddit}")
            return contributors[:limit]  # Return top contributors
        
        except Exception as e:
            logger.error(f"Error finding contributors in r/{subreddit}: {e}")
            return []


# Sample usage
if __name__ == "__main__":
    # Initialize fetcher
    user_fetcher = RedditUserFetcher()
    
    # Example 1: Get basic profile info
    username = "diegocaples"  # Replace with a real username
    profile = user_fetcher.get_user_profile(username)
    print(f"\nProfile for {username}:")
    print(f"- Karma: {profile.get('comment_karma', 0) + profile.get('link_karma', 0)}")
    print(f"- Account created: {profile.get('created_utc', 'Unknown')}")
    
    # Example 2: Get user's top posts
    print(f"\nTop posts by {username}:")
    posts = user_fetcher.get_user_submissions(username, limit=5)
    for i, post in enumerate(posts, 1):
        print(f"{i}. {post.get('title', 'No title')} (Score: {post.get('score', 0)})")
    
    # Example 3: Analyze a user's contributions
    print(f"\nAnalyzing contributions for {username}...")
    analysis = user_fetcher.analyze_user_contributions(username, time_period_days=90)
    
    print(f"Activity in the past 90 days:")
    print(f"- Total submissions: {analysis.get('activity_summary', {}).get('total_submissions', 0)}")
    print(f"- Total comments: {analysis.get('activity_summary', {}).get('total_comments', 0)}")
    
    print("\nTop subreddits:")
    for i, subreddit in enumerate(analysis.get('top_subreddits', [])[:3], 1):
        print(f"{i}. r/{subreddit.get('subreddit')}: {subreddit.get('submissions')} posts, {subreddit.get('comments')} comments")
    
    print("\nPotential expertise areas:")
    for area in analysis.get('potential_expertise', []):
        print(f"- r/{area}")
    
    # Example 4: Find valuable contributors in a subreddit
    subreddit = "LocalLLaMA"
    print(f"\nMost valuable contributors in r/{subreddit}:")
    contributors = user_fetcher.find_most_valuable_contributors(subreddit, time_filter="month", limit=5)
    
    for i, contributor in enumerate(contributors, 1):
        print(f"{i}. u/{contributor.get('username')}")
        print(f"   - Total karma: {contributor.get('total_karma', 0)}")
        print(f"   - Posts: {contributor.get('post_count', 0)}, Comments: {contributor.get('comment_count', 0)}")
    
    # Example 5: Get user trophies and expertise analysis
    print(f"\nFetching trophies and expertise analysis for {username}:")
    trophies = user_fetcher.get_user_trophies(username)
    
    print(f"User has {len(trophies)} trophies:")
    for i, trophy in enumerate(trophies, 1):
        print(f"{i}. {trophy.get('name', 'Unknown Trophy')}")
        if trophy.get('description'):
            print(f"   - Description: {trophy.get('description')}")
        if trophy.get('granted_at'):
            print(f"   - Awarded: {trophy.get('granted_at')}")
    
    # Get comprehensive expertise analysis
    expertise = user_fetcher.analyze_user_expertise_with_trophies(username)
    print(f"\nExpertise Analysis for {username}:")
    print(f"- Expertise Score: {expertise.get('expertise_score', 0)}/100")
    print(f"- Expertise Ranking: {expertise.get('expertise_ranking', 'Unknown')}")
    print(f"- Trophy Count: {expertise.get('trophy_count', 0)}")
    
    print("\nExpertise Trophies:")
    for i, trophy_info in enumerate(expertise.get('expertise_trophies', []), 1):
        if i <= 3:  # Show top 3
            trophy = trophy_info.get('trophy', {})
            print(f"{i}. {trophy.get('name', 'Unknown')} - {trophy_info.get('relevance', 'General')}") 