"""
Sentiment Trend Analysis for Reddit AI Technologies

Analyzes sentiment trends over time to identify emerging technologies,
growing interest, and shifting community perception.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentTrendAnalyzer:
    """Analyzes sentiment trends over time to identify technology patterns."""
    
    def __init__(self):
        """Initialize the sentiment trend analyzer."""
        logger.info("Initializing SentimentTrendAnalyzer")
    
    def prepare_time_series_data(self, 
                               posts: List[Dict[str, Any]], 
                               time_field: str = 'created_utc',
                               min_posts_per_topic: int = 5) -> pd.DataFrame:
        """
        Prepare time series data from posts with sentiment data.
        
        Args:
            posts: List of posts with sentiment data
            time_field: Field name containing timestamp
            min_posts_per_topic: Minimum posts required for a topic to be included
            
        Returns:
            DataFrame with sentiment time series data
        """
        logger.info("Preparing time series data for sentiment analysis")
        
        # Ensure posts have sentiment data
        valid_posts = [p for p in posts if 'sentiment' in p]
        
        if not valid_posts:
            logger.warning("No posts with sentiment data found")
            return pd.DataFrame()
        
        # Extract basic data from posts
        rows = []
        for post in valid_posts:
            # Skip if missing critical fields
            if time_field not in post or not post.get('title'):
                continue
                
            # Get timestamp
            created_time = post[time_field]
            if isinstance(created_time, (int, float)):
                # Convert Unix timestamp to datetime
                timestamp = datetime.fromtimestamp(created_time)
            elif isinstance(created_time, str):
                # Try to parse string datetime
                try:
                    timestamp = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                except ValueError:
                    # If parse fails, skip this post
                    continue
            else:
                # Unknown format, skip
                continue
            
            # Get sentiment scores
            sentiment = post.get('sentiment', {}).get('overall', {})
            if not sentiment:
                continue
                
            # Get topics from category, flair, or other fields
            topics = []
            if 'category' in post and post['category']:
                topics.append(post['category'])
            if 'link_flair_text' in post and post['link_flair_text']:
                topics.append(post['link_flair_text'])
                
            # If no topics found, use 'General'
            if not topics:
                topics = ['General']
            
            # Create row for each topic
            for topic in topics:
                row = {
                    'timestamp': timestamp,
                    'topic': topic,
                    'compound_score': sentiment.get('compound', 0),
                    'positive_score': sentiment.get('positive', 0),
                    'negative_score': sentiment.get('negative', 0),
                    'neutral_score': sentiment.get('neutral', 0),
                    'post_id': post.get('id', ''),
                    'title': post.get('title', ''),
                    'score': post.get('score', 0),
                    'num_comments': post.get('num_comments', 0)
                }
                rows.append(row)
        
        # Create DataFrame
        df = pd.DataFrame(rows)
        
        if df.empty:
            logger.warning("No valid sentiment data could be extracted")
            return df
            
        # Filter out topics with too few posts
        topic_counts = df['topic'].value_counts()
        valid_topics = topic_counts[topic_counts >= min_posts_per_topic].index
        df = df[df['topic'].isin(valid_topics)]
        
        logger.info(f"Prepared time series data with {len(df)} entries across {len(valid_topics)} topics")
        return df
    
    def analyze_sentiment_trends(self, 
                               df: pd.DataFrame, 
                               timeframe: str = 'day',
                               min_data_points: int = 3) -> Dict[str, Any]:
        """
        Analyze sentiment trends over time.
        
        Args:
            df: DataFrame with sentiment time series data
            timeframe: Time grouping ('hour', 'day', 'week', 'month')
            min_data_points: Minimum data points required for trend analysis
            
        Returns:
            Dictionary with trend analysis results
        """
        if df.empty:
            return {'error': 'No data available for trend analysis'}
            
        logger.info(f"Analyzing sentiment trends with {timeframe} grouping")
        
        # Set up time grouping
        if timeframe == 'hour':
            time_group = df['timestamp'].dt.floor('H')
        elif timeframe == 'week':
            time_group = df['timestamp'].dt.to_period('W').dt.start_time
        elif timeframe == 'month':
            time_group = df['timestamp'].dt.to_period('M').dt.start_time
        else:  # default to day
            time_group = df['timestamp'].dt.floor('D')
            
        df['time_group'] = time_group
        
        # Calculate grouped statistics
        grouped = df.groupby(['time_group', 'topic']).agg({
            'compound_score': 'mean',
            'positive_score': 'mean',
            'negative_score': 'mean',
            'score': 'mean',
            'num_comments': 'mean',
            'post_id': 'count'
        }).reset_index()
        
        grouped = grouped.rename(columns={'post_id': 'post_count'})
        
        # Calculate trends for each topic
        topics = df['topic'].unique()
        trend_results = {}
        
        for topic in topics:
            topic_data = grouped[grouped['topic'] == topic].sort_values('time_group')
            
            # Skip if too few data points
            if len(topic_data) < min_data_points:
                continue
                
            # Calculate sentiment trend (linear regression)
            x = np.arange(len(topic_data))
            y = topic_data['compound_score'].values
            
            if len(x) > 1 and len(y) > 1:  # Need at least 2 points for regression
                slope, intercept = np.polyfit(x, y, 1)
                trend = slope * (len(x) - 1)  # Trend over entire period
            else:
                slope = 0
                trend = 0
            
            # Calculate engagement trends
            if len(x) > 1:
                score_slope, _ = np.polyfit(x, topic_data['score'].values, 1)
                comments_slope, _ = np.polyfit(x, topic_data['num_comments'].values, 1)
                volume_slope, _ = np.polyfit(x, topic_data['post_count'].values, 1)
            else:
                score_slope = comments_slope = volume_slope = 0
            
            # Calculate volatility (standard deviation of changes)
            sentiment_changes = topic_data['compound_score'].diff().dropna()
            volatility = sentiment_changes.std() if len(sentiment_changes) > 0 else 0
            
            # Store results
            trend_results[topic] = {
                'current_sentiment': float(y[-1]) if len(y) > 0 else 0,
                'sentiment_trend': float(trend),
                'sentiment_slope': float(slope),
                'sentiment_volatility': float(volatility),
                'post_volume_trend': float(volume_slope),
                'engagement_trends': {
                    'score': float(score_slope),
                    'comments': float(comments_slope)
                },
                'data_points': len(topic_data),
                'first_date': topic_data['time_group'].min(),
                'last_date': topic_data['time_group'].max(),
                'time_series': topic_data.to_dict('records')
            }
        
        # Find emerging and fading topics
        topics_with_trends = [(topic, data['sentiment_trend'], data['post_volume_trend']) 
                             for topic, data in trend_results.items()]
        
        if topics_with_trends:
            # Sort by combined trend score (sentiment + volume)
            sorted_trends = sorted(topics_with_trends, 
                                  key=lambda x: x[1] + x[2], 
                                  reverse=True)
            
            emerging_topics = [t[0] for t in sorted_trends[:3]]
            fading_topics = [t[0] for t in sorted_trends[-3:]]
        else:
            emerging_topics = []
            fading_topics = []
        
        # Overall analysis
        analysis = {
            'topics': trend_results,
            'timeframe': timeframe,
            'emerging_topics': emerging_topics,
            'fading_topics': fading_topics,
            'most_volatile_topic': max(trend_results.items(), 
                                      key=lambda x: x[1]['sentiment_volatility'])[0] 
                                    if trend_results else None,
            'strongest_positive_trend': max(trend_results.items(),
                                          key=lambda x: x[1]['sentiment_trend'])[0]
                                      if trend_results else None,
            'strongest_negative_trend': min(trend_results.items(),
                                          key=lambda x: x[1]['sentiment_trend'])[0]
                                      if trend_results else None,
            'analysis_time': datetime.now().isoformat()
        }
        
        logger.info(f"Completed sentiment trend analysis for {len(trend_results)} topics")
        return analysis
    
    def identify_tech_trends(self, 
                           posts: List[Dict[str, Any]], 
                           timeframe: str = 'day',
                           sentiment_threshold: float = 0.2,
                           engagement_threshold: float = 0.0) -> Dict[str, Any]:
        """
        Identify technology trends based on sentiment and engagement patterns.
        
        Args:
            posts: List of posts with sentiment data
            timeframe: Time grouping for analysis
            sentiment_threshold: Minimum sentiment change to identify a trend
            engagement_threshold: Minimum engagement change to identify a trend
            
        Returns:
            Dictionary with tech trend analysis
        """
        logger.info("Identifying technology trends")
        
        # Prepare time series data
        df = self.prepare_time_series_data(posts)
        
        if df.empty:
            return {'error': 'No data available for trend analysis'}
        
        # Analyze sentiment trends
        trends = self.analyze_sentiment_trends(df, timeframe)
        
        if 'error' in trends:
            return trends
        
        # Identify technology categories
        tech_categories = {
            'AI Models': ['GPT', 'LLM', 'BERT', 'Transformer', 'Neural Network', 'Model'],
            'AI Applications': ['Chatbot', 'Assistant', 'App', 'Tool', 'Software'],
            'Research Areas': ['Research', 'Paper', 'Study', 'Algorithm'],
            'Companies': ['OpenAI', 'Google', 'Microsoft', 'Anthropic', 'Meta', 'Company'],
            'Concepts': ['Ethics', 'Alignment', 'Safety', 'Privacy', 'Bias']
        }
        
        # Categorize topics
        categorized_topics = {}
        for topic, data in trends['topics'].items():
            # Find matching category
            matched_category = None
            for category, keywords in tech_categories.items():
                if any(keyword.lower() in topic.lower() for keyword in keywords):
                    matched_category = category
                    break
            
            # Use 'Other' if no match found
            if not matched_category:
                matched_category = 'Other'
                
            # Add to categorized topics
            if matched_category not in categorized_topics:
                categorized_topics[matched_category] = []
                
            categorized_topics[matched_category].append({
                'topic': topic,
                'sentiment_trend': data['sentiment_trend'],
                'volume_trend': data['post_volume_trend'],
                'current_sentiment': data['current_sentiment']
            })
                
        # Identify significant trends
        significant_trends = []
        for topic, data in trends['topics'].items():
            # Check if sentiment or engagement trends are significant
            if (abs(data['sentiment_trend']) >= sentiment_threshold or 
                data['post_volume_trend'] >= engagement_threshold):
                
                trend_direction = 'positive' if data['sentiment_trend'] > 0 else 'negative'
                volume_direction = 'increasing' if data['post_volume_trend'] > 0 else 'decreasing'
                
                significant_trends.append({
                    'topic': topic,
                    'sentiment_trend': data['sentiment_trend'],
                    'volume_trend': data['post_volume_trend'],
                    'current_sentiment': data['current_sentiment'],
                    'data_points': data['data_points'],
                    'trend_description': f"{topic} shows {trend_direction} sentiment trend with {volume_direction} discussion volume"
                })
        
        # Sort by combined impact (sentiment change + volume change)
        significant_trends.sort(
            key=lambda x: abs(x['sentiment_trend']) + abs(x['volume_trend']), 
            reverse=True
        )
        
        # Generate trend analysis
        tech_trend_analysis = {
            'timeframe': timeframe,
            'categorized_topics': categorized_topics,
            'significant_trends': significant_trends[:5],  # Top 5 most significant
            'emerging_technologies': [
                trends['topics'][topic] for topic in trends['emerging_topics']
                if topic in trends['topics']
            ],
            'fading_technologies': [
                trends['topics'][topic] for topic in trends['fading_topics']
                if topic in trends['topics']
            ],
            'insights': self._generate_trend_insights(trends, categorized_topics),
            'analysis_time': datetime.now().isoformat()
        }
        
        logger.info(f"Identified {len(significant_trends)} significant technology trends")
        return tech_trend_analysis
    
    def generate_trend_report(self, 
                           posts: List[Dict[str, Any]], 
                           timeframe: str = 'day') -> str:
        """
        Generate a markdown report on technology sentiment trends.
        
        Args:
            posts: List of posts with sentiment data
            timeframe: Time grouping for analysis
            
        Returns:
            Markdown formatted trend report
        """
        # Identify technology trends
        trend_analysis = self.identify_tech_trends(posts, timeframe)
        
        if 'error' in trend_analysis:
            return f"## Error in Trend Analysis\n\n{trend_analysis['error']}"
        
        # Generate report
        report = ["## AI Technology Sentiment Trends\n"]
        
        # Time period
        if timeframe == 'day':
            period = "Daily"
        elif timeframe == 'week':
            period = "Weekly"
        elif timeframe == 'month':
            period = "Monthly"
        else:
            period = "Recent"
            
        report.append(f"### {period} Trend Analysis\n")
        
        # Emerging technologies
        report.append("#### Emerging Technologies\n")
        if trend_analysis['emerging_technologies']:
            for tech in trend_analysis['emerging_technologies']:
                sentiment_desc = "positive" if tech['sentiment_trend'] > 0 else "negative"
                report.append(f"- **{tech.get('topic', 'Unknown')}**: "
                             f"Showing {sentiment_desc} sentiment trend "
                             f"({tech['sentiment_trend']:.2f}) with "
                             f"{'increasing' if tech['post_volume_trend'] > 0 else 'stable'} "
                             f"discussion volume")
        else:
            report.append("No clear emerging technologies identified in this period.")
        
        report.append("")
        
        # Significant trends
        report.append("#### Most Significant Trends\n")
        if trend_analysis['significant_trends']:
            for trend in trend_analysis['significant_trends']:
                report.append(f"- **{trend['topic']}**: {trend['trend_description']}")
        else:
            report.append("No significant trends identified in this period.")
        
        report.append("")
        
        # Category analysis
        report.append("### Technology Category Analysis\n")
        for category, topics in trend_analysis['categorized_topics'].items():
            if not topics:
                continue
                
            report.append(f"#### {category}\n")
            
            # Sort by sentiment trend
            sorted_topics = sorted(topics, key=lambda x: x['sentiment_trend'], reverse=True)
            
            for topic in sorted_topics[:3]:  # Top 3 per category
                trend = topic['sentiment_trend']
                sentiment = "positive" if trend > 0 else "negative" if trend < 0 else "neutral"
                report.append(f"- **{topic['topic']}**: "
                             f"{sentiment.capitalize()} trend ({trend:.2f})")
            
            report.append("")
        
        # Insights
        report.append("### Key Insights\n")
        for insight in trend_analysis['insights']:
            report.append(f"- {insight}")
        
        return "\n".join(report)
    
    def generate_trend_chart(self,
                           posts: List[Dict[str, Any]],
                           topics: Optional[List[str]] = None,
                           timeframe: str = 'day') -> Optional[str]:
        """
        Generate a base64-encoded chart image showing sentiment trends.
        
        Args:
            posts: List of posts with sentiment data
            topics: Specific topics to include (None for auto-selection)
            timeframe: Time grouping for analysis
            
        Returns:
            Base64-encoded image string or None if chart cannot be generated
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
        except ImportError:
            logger.warning("Matplotlib not available for chart generation")
            return None
            
        # Prepare time series data
        df = self.prepare_time_series_data(posts)
        
        if df.empty:
            logger.warning("No data available for chart generation")
            return None
            
        # Set up time grouping
        if timeframe == 'hour':
            time_group = df['timestamp'].dt.floor('H')
        elif timeframe == 'week':
            time_group = df['timestamp'].dt.to_period('W').dt.start_time
        elif timeframe == 'month':
            time_group = df['timestamp'].dt.to_period('M').dt.start_time
        else:  # default to day
            time_group = df['timestamp'].dt.floor('D')
            
        df['time_group'] = time_group
        
        # Choose topics if not specified
        if not topics:
            # Get top topics by post count
            top_topics = df['topic'].value_counts().head(5).index.tolist()
            topics = top_topics
            
        # Filter to selected topics
        df_filtered = df[df['topic'].isin(topics)]
        
        if df_filtered.empty:
            logger.warning("No data available for selected topics")
            return None
            
        # Calculate grouped statistics
        grouped = df_filtered.groupby(['time_group', 'topic']).agg({
            'compound_score': 'mean'
        }).reset_index()
        
        # Create pivot table for plotting
        pivot = grouped.pivot(index='time_group', columns='topic', values='compound_score')
        
        # Generate plot
        plt.figure(figsize=(10, 6))
        pivot.plot(marker='o', linestyle='-')
        
        plt.title('Sentiment Trends Over Time')
        plt.xlabel('Date')
        plt.ylabel('Sentiment Score')
        plt.grid(True, alpha=0.3)
        plt.legend(title='Topic')
        plt.tight_layout()
        
        # Save to bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        
        # Convert to base64
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        return img_str
    
    def _generate_trend_insights(self, 
                               trends: Dict[str, Any], 
                               categorized_topics: Dict[str, List]) -> List[str]:
        """Generate insights from trend analysis results."""
        insights = []
        
        # Overall sentiment direction
        positive_topics = sum(1 for t in trends['topics'].values() 
                            if t['sentiment_trend'] > 0.1)
        negative_topics = sum(1 for t in trends['topics'].values() 
                            if t['sentiment_trend'] < -0.1)
        total_topics = len(trends['topics'])
        
        if total_topics > 0:
            if positive_topics > negative_topics and positive_topics > total_topics * 0.6:
                insights.append("Overall AI sentiment is trending positive across most technologies")
            elif negative_topics > positive_topics and negative_topics > total_topics * 0.6:
                insights.append("Overall AI sentiment is trending negative across most technologies")
            else:
                insights.append("AI sentiment shows mixed trends with no clear overall direction")
        
        # Category-specific insights
        for category, topics in categorized_topics.items():
            if not topics:
                continue
                
            # Calculate average trends for this category
            avg_sentiment_trend = np.mean([t['sentiment_trend'] for t in topics])
            avg_volume_trend = np.mean([t['volume_trend'] for t in topics])
            
            if abs(avg_sentiment_trend) > 0.15:
                direction = "positive" if avg_sentiment_trend > 0 else "negative"
                insights.append(f"{category} technologies are showing {direction} sentiment trends")
                
            if avg_volume_trend > 0.5:
                insights.append(f"Discussion volume for {category} is significantly increasing")
            elif avg_volume_trend < -0.5:
                insights.append(f"Discussion volume for {category} is significantly decreasing")
        
        # Specific technology insights
        if trends['strongest_positive_trend']:
            topic = trends['strongest_positive_trend']
            insights.append(f"{topic} is showing the strongest positive sentiment shift")
            
        if trends['strongest_negative_trend']:
            topic = trends['strongest_negative_trend']
            insights.append(f"{topic} is showing the strongest negative sentiment shift")
            
        if trends['most_volatile_topic']:
            topic = trends['most_volatile_topic']
            insights.append(f"{topic} shows the most volatile sentiment, indicating controversial status")
        
        return insights
        
# Example usage
if __name__ == "__main__":
    # Create sample data for testing
    sample_posts = [
        {
            'title': 'GPT-5 impressions after one week',
            'selftext': 'The performance is incredible. Best model ever released.',
            'category': 'LLM',
            'created_utc': (datetime.now() - timedelta(days=1)).timestamp(),
            'score': 120,
            'num_comments': 45,
            'sentiment': {
                'overall': {
                    'compound': 0.8,
                    'positive': 0.9,
                    'negative': 0.0,
                    'neutral': 0.1,
                    'sentiment': 'positive'
                }
            }
        },
        {
            'title': 'GPT-5 accuracy issues',
            'selftext': 'Finding some problems with factual accuracy.',
            'category': 'LLM',
            'created_utc': (datetime.now() - timedelta(days=2)).timestamp(),
            'score': 80,
            'num_comments': 30,
            'sentiment': {
                'overall': {
                    'compound': -0.2,
                    'positive': 0.1,
                    'negative': 0.3,
                    'neutral': 0.6,
                    'sentiment': 'negative'
                }
            }
        },
        {
            'title': 'New AutoGPT features are amazing',
            'selftext': 'The latest version has improved significantly.',
            'category': 'AI Agents',
            'created_utc': datetime.now().timestamp(),
            'score': 95,
            'num_comments': 40,
            'sentiment': {
                'overall': {
                    'compound': 0.6,
                    'positive': 0.7,
                    'negative': 0.0,
                    'neutral': 0.3,
                    'sentiment': 'positive'
                }
            }
        },
        {
            'title': 'AutoGPT vs AgentGPT comparison',
            'selftext': 'Both have strengths and weaknesses.',
            'category': 'AI Agents',
            'created_utc': (datetime.now() - timedelta(days=3)).timestamp(),
            'score': 70,
            'num_comments': 25,
            'sentiment': {
                'overall': {
                    'compound': 0.1,
                    'positive': 0.4,
                    'negative': 0.3,
                    'neutral': 0.3,
                    'sentiment': 'neutral'
                }
            }
        },
    ]
    
    # Add more sample data for LLM category with different dates
    for i in range(5):
        days_ago = i + 4
        sentiment = 0.2 - (i * 0.1)  # Declining sentiment trend
        
        sample_posts.append({
            'title': f'GPT-5 daily update {i+1}',
            'selftext': f'Day {i+1} of using GPT-5.',
            'category': 'LLM',
            'created_utc': (datetime.now() - timedelta(days=days_ago)).timestamp(),
            'score': 50 - (i * 5),
            'num_comments': 20 - (i * 2),
            'sentiment': {
                'overall': {
                    'compound': sentiment,
                    'positive': max(0, sentiment),
                    'negative': max(0, -sentiment),
                    'neutral': 0.5,
                    'sentiment': 'positive' if sentiment > 0.05 else 'negative' if sentiment < -0.05 else 'neutral'
                }
            }
        })
    
    # Add more sample data for AI Agents with increasing sentiment
    for i in range(5):
        days_ago = i + 4
        sentiment = 0.0 + (i * 0.15)  # Increasing sentiment trend
        
        sample_posts.append({
            'title': f'AutoGPT experiment {i+1}',
            'selftext': f'Experiment {i+1} with AutoGPT.',
            'category': 'AI Agents',
            'created_utc': (datetime.now() - timedelta(days=days_ago)).timestamp(),
            'score': 30 + (i * 8),
            'num_comments': 15 + (i * 3),
            'sentiment': {
                'overall': {
                    'compound': sentiment,
                    'positive': max(0, sentiment),
                    'negative': max(0, -sentiment),
                    'neutral': 0.5,
                    'sentiment': 'positive' if sentiment > 0.05 else 'negative' if sentiment < -0.05 else 'neutral'
                }
            }
        })
    
    # Initialize analyzer
    trend_analyzer = SentimentTrendAnalyzer()
    
    # Generate trend report
    report = trend_analyzer.generate_trend_report(sample_posts)
    
    # Print report
    print(report) 