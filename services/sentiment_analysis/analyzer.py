"""
Sentiment Analysis for Reddit AI Trend Reports

Analyzes sentiment in Reddit posts and comments to identify emotional trends
related to AI technologies and topics.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Analyzes sentiment in Reddit content."""
    
    def __init__(self, use_advanced_model: bool = False):
        """
        Initialize the sentiment analyzer.
        
        Args:
            use_advanced_model: Whether to use advanced transformer-based model
                               (more accurate but slower)
        """
        # Download required NLTK resources if not already available
        try:
            nltk.data.find('sentiment/vader_lexicon.zip')
        except LookupError:
            nltk.download('vader_lexicon')
        
        # Initialize VADER sentiment analyzer
        self.sia = SentimentIntensityAnalyzer()
        
        # Initialize advanced model if requested
        self.advanced_model = None
        if use_advanced_model:
            try:
                from transformers import pipeline
                logger.info("Loading advanced sentiment model...")
                self.advanced_model = pipeline(
                    "sentiment-analysis",
                    model="distilbert-base-uncased-finetuned-sst-2-english"
                )
            except ImportError:
                logger.warning("transformers library not available. Advanced model will not be used.")
    
    def analyze_text(self, text: str, use_advanced: bool = False) -> Dict[str, Any]:
        """
        Analyze sentiment of a text string.
        
        Args:
            text: Text to analyze
            use_advanced: Whether to use the advanced model
            
        Returns:
            Dictionary with sentiment scores
        """
        if not text or len(text.strip()) == 0:
            return {
                'compound': 0,
                'positive': 0,
                'negative': 0,
                'neutral': 0,
                'sentiment': 'neutral'
            }
        
        # Get VADER sentiment
        vader_scores = self.sia.polarity_scores(text)
        
        # Add TextBlob sentiment for comparison
        blob = TextBlob(text)
        textblob_polarity = blob.sentiment.polarity
        textblob_subjectivity = blob.sentiment.subjectivity
        
        # Determine overall sentiment label
        compound = vader_scores['compound']
        if compound >= 0.05:
            sentiment = 'positive'
        elif compound <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        # Use advanced model if requested and available
        advanced_score = None
        if use_advanced and self.advanced_model:
            try:
                # Limit text length for transformer model
                truncated_text = text[:512]
                result = self.advanced_model(truncated_text)[0]
                advanced_score = {
                    'label': result['label'],
                    'score': result['score']
                }
            except Exception as e:
                logger.warning(f"Advanced model error: {e}")
        
        # Return combined results
        return {
            'compound': vader_scores['compound'],
            'positive': vader_scores['pos'],
            'negative': vader_scores['neg'],
            'neutral': vader_scores['neu'],
            'textblob_polarity': textblob_polarity,
            'textblob_subjectivity': textblob_subjectivity,
            'advanced': advanced_score,
            'sentiment': sentiment
        }
    
    def analyze_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a list of posts.
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            Posts with added sentiment data
        """
        logger.info(f"Analyzing sentiment for {len(posts)} posts")
        
        enhanced_posts = []
        for post in posts:
            # Analyze title sentiment
            title_sentiment = self.analyze_text(post.get('title', ''))
            
            # Analyze content sentiment (if available)
            content_text = post.get('selftext', '') or post.get('body', '')
            content_sentiment = self.analyze_text(content_text) if content_text else None
            
            # Combine title and content for overall sentiment
            combined_text = f"{post.get('title', '')} {content_text}"
            overall_sentiment = self.analyze_text(combined_text)
            
            # Add sentiment data to post
            enhanced_post = post.copy()
            enhanced_post['sentiment'] = {
                'title': title_sentiment,
                'content': content_sentiment,
                'overall': overall_sentiment
            }
            
            enhanced_posts.append(enhanced_post)
        
        logger.info(f"Completed sentiment analysis for {len(enhanced_posts)} posts")
        return enhanced_posts
    
    def analyze_topic_sentiment(self, 
                              posts: List[Dict[str, Any]], 
                              topics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze sentiment across various topics.
        
        Args:
            posts: List of posts with sentiment data
            topics: Optional list of specific topics to analyze
                   If None, will extract topics from post categories/flairs
            
        Returns:
            Dictionary containing topic sentiment analysis
        """
        logger.info("Analyzing topic sentiment")
        
        # Extract topics if not provided
        if not topics:
            # Try to extract from categories or flairs
            topic_set = set()
            for post in posts:
                if 'category' in post and post['category']:
                    topic_set.add(post['category'])
                if 'link_flair_text' in post and post['link_flair_text']:
                    topic_set.add(post['link_flair_text'])
            
            topics = list(topic_set)
        
        # Initialize topic sentiment tracking
        topic_sentiment = {topic: {
            'posts': [],
            'compound_scores': [],
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        } for topic in topics}
        
        # Generic topic for posts without specific topic
        topic_sentiment['General'] = {
            'posts': [],
            'compound_scores': [],
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }
        
        # Categorize posts by topic and track sentiment
        for post in posts:
            if 'sentiment' not in post:
                continue
                
            post_sentiment = post['sentiment']['overall']['sentiment']
            compound_score = post['sentiment']['overall']['compound']
            
            # Determine which topic(s) this post belongs to
            post_topics = []
            for topic in topics:
                if (('category' in post and post['category'] == topic) or
                    ('link_flair_text' in post and post['link_flair_text'] == topic) or
                    (topic.lower() in post.get('title', '').lower())):
                    post_topics.append(topic)
            
            # If no specific topics found, add to General
            if not post_topics:
                post_topics = ['General']
            
            # Add post to each relevant topic
            for topic in post_topics:
                topic_sentiment[topic]['posts'].append(post)
                topic_sentiment[topic]['compound_scores'].append(compound_score)
                
                if post_sentiment == 'positive':
                    topic_sentiment[topic]['positive_count'] += 1
                elif post_sentiment == 'negative':
                    topic_sentiment[topic]['negative_count'] += 1
                else:
                    topic_sentiment[topic]['neutral_count'] += 1
        
        # Calculate aggregate statistics for each topic
        topic_summary = {}
        for topic, data in topic_sentiment.items():
            if len(data['posts']) == 0:
                continue
                
            total_posts = len(data['posts'])
            
            topic_summary[topic] = {
                'post_count': total_posts,
                'average_compound': np.mean(data['compound_scores']) if data['compound_scores'] else 0,
                'sentiment_distribution': {
                    'positive': data['positive_count'] / total_posts,
                    'negative': data['negative_count'] / total_posts,
                    'neutral': data['neutral_count'] / total_posts,
                },
                'dominant_sentiment': max(
                    ['positive', 'negative', 'neutral'],
                    key=lambda s: data[f'{s}_count']
                ),
                'sentiment_strength': abs(np.mean(data['compound_scores']) if data['compound_scores'] else 0)
            }
        
        # Generate topic sentiment summary
        analysis = {
            'topics': topic_summary,
            'overall': {
                'most_positive_topic': max(
                    topic_summary.keys(), 
                    key=lambda t: topic_summary[t]['average_compound']
                ) if topic_summary else None,
                'most_negative_topic': min(
                    topic_summary.keys(), 
                    key=lambda t: topic_summary[t]['average_compound']
                ) if topic_summary else None,
                'most_controversial_topic': max(
                    topic_summary.keys(),
                    key=lambda t: topic_summary[t]['sentiment_strength']
                ) if topic_summary else None
            }
        }
        
        logger.info(f"Completed topic sentiment analysis for {len(topics)} topics")
        return analysis

    def generate_sentiment_report(self, 
                                posts: List[Dict[str, Any]], 
                                topics: Optional[List[str]] = None) -> str:
        """
        Generate a markdown report on sentiment analysis.
        
        Args:
            posts: List of posts with sentiment data
            topics: Optional list of specific topics to analyze
            
        Returns:
            Markdown formatted sentiment report
        """
        # First analyze sentiment if not already done
        if posts and 'sentiment' not in posts[0]:
            posts = self.analyze_posts(posts)
        
        # Analyze topic sentiment
        topic_analysis = self.analyze_topic_sentiment(posts, topics)
        
        # Get overall sentiment stats
        positive_count = sum(1 for p in posts if p.get('sentiment', {}).get('overall', {}).get('sentiment') == 'positive')
        negative_count = sum(1 for p in posts if p.get('sentiment', {}).get('overall', {}).get('sentiment') == 'negative')
        neutral_count = sum(1 for p in posts if p.get('sentiment', {}).get('overall', {}).get('sentiment') == 'neutral')
        total_posts = len(posts)
        
        # Calculate average compound score
        compound_scores = [p.get('sentiment', {}).get('overall', {}).get('compound', 0) for p in posts]
        avg_compound = np.mean(compound_scores) if compound_scores else 0
        
        # Generate markdown report
        report = ["## Sentiment Analysis\n"]
        
        # Overall community sentiment
        report.append("### Overall Community Sentiment\n")
        report.append(f"The AI community's overall sentiment is **{self._describe_sentiment(avg_compound)}** with an average sentiment score of {avg_compound:.2f}.\n")
        
        report.append("**Sentiment Distribution:**\n")
        report.append(f"- Positive: {positive_count} posts ({positive_count/total_posts*100:.1f}%)")
        report.append(f"- Negative: {negative_count} posts ({negative_count/total_posts*100:.1f}%)")
        report.append(f"- Neutral: {neutral_count} posts ({neutral_count/total_posts*100:.1f}%)\n")
        
        # Topic sentiment
        report.append("### Topic Sentiment Analysis\n")
        
        if topic_analysis['overall']['most_positive_topic']:
            most_positive = topic_analysis['overall']['most_positive_topic']
            score = topic_analysis['topics'][most_positive]['average_compound']
            report.append(f"**Most Positive Topic**: {most_positive} (Score: {score:.2f})")
            
        if topic_analysis['overall']['most_negative_topic']:
            most_negative = topic_analysis['overall']['most_negative_topic']
            score = topic_analysis['topics'][most_negative]['average_compound']
            report.append(f"**Most Negative Topic**: {most_negative} (Score: {score:.2f})")
            
        if topic_analysis['overall']['most_controversial_topic']:
            most_controversial = topic_analysis['overall']['most_controversial_topic']
            strength = topic_analysis['topics'][most_controversial]['sentiment_strength']
            report.append(f"**Most Controversial Topic**: {most_controversial} (Intensity: {strength:.2f})\n")
        
        # Detailed topic breakdown
        report.append("### Detailed Topic Sentiment\n")
        report.append("| Topic | Posts | Avg. Sentiment | Dominant Mood |")
        report.append("|-------|-------|----------------|---------------|")
        
        for topic, data in sorted(
            topic_analysis['topics'].items(), 
            key=lambda x: x[1]['average_compound'], 
            reverse=True
        ):
            avg_score = data['average_compound']
            sentiment_desc = self._describe_sentiment(avg_score)
            dominant = data['dominant_sentiment'].capitalize()
            report.append(f"| {topic} | {data['post_count']} | {avg_score:.2f} | {dominant} |")
        
        # Sentiment insights
        report.append("\n### Sentiment Insights\n")
        
        # General insights based on the data
        if avg_compound > 0.2:
            report.append("- The AI community is showing significant optimism about current developments")
        elif avg_compound < -0.2:
            report.append("- There is notable concern or skepticism in the AI community currently")
        else:
            report.append("- The community shows a balanced perspective on current AI developments")
            
        # Add topic-specific insights
        for topic, data in topic_analysis['topics'].items():
            if topic == 'General':
                continue
                
            score = data['average_compound']
            if abs(score) > 0.2 and data['post_count'] >= 3:
                sentiment = "positive" if score > 0 else "negative"
                report.append(f"- {topic} is generating {sentiment} sentiment (Score: {score:.2f})")
        
        return "\n".join(report)
    
    def _describe_sentiment(self, score: float) -> str:
        """Return a descriptive word for a sentiment score."""
        if score >= 0.5:
            return "very positive"
        elif score >= 0.2:
            return "positive"
        elif score > -0.2:
            return "neutral"
        elif score > -0.5:
            return "negative"
        else:
            return "very negative"


# Example usage
if __name__ == "__main__":
    # Create sample data for testing
    sample_posts = [
        {
            'title': 'I love the new GPT-5 model, it\'s amazing!',
            'selftext': 'The performance improvements are incredible. Best model ever released.',
            'category': 'LLM',
            'score': 120,
            'num_comments': 45
        },
        {
            'title': 'Disappointed with the latest update',
            'selftext': 'The new features don\'t work well. Many bugs and problems.',
            'category': 'Software',
            'score': 30,
            'num_comments': 78
        },
        {
            'title': 'Neutral review of AutoGPT',
            'selftext': 'It has some good features and some limitations. Works for some use cases.',
            'category': 'AI Agents',
            'score': 50,
            'num_comments': 25
        }
    ]
    
    # Initialize analyzer
    analyzer = SentimentAnalyzer()
    
    # Analyze posts
    analyzed_posts = analyzer.analyze_posts(sample_posts)
    
    # Generate report
    report = analyzer.generate_sentiment_report(analyzed_posts)
    
    # Print report
    print(report) 