"""
Sentiment Analysis Module for Reddit AI Trend Reports

This module provides sentiment analysis capabilities for Reddit posts and comments,
helping identify emotional trends related to AI technologies and topics.
"""

from services.sentiment_analysis.analyzer import SentimentAnalyzer
from services.sentiment_analysis.trend_analyzer import SentimentTrendAnalyzer

# Export classes
__all__ = ['SentimentAnalyzer', 'SentimentTrendAnalyzer'] 