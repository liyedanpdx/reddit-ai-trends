"""
YouTube Transcript Enricher
Extracts video transcripts and generates summaries using LLM
"""
import re
import logging
import sys
import os
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from openai import OpenAI

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.llm_processing.core.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class YouTubeEnricher:
    """Enriches posts with YouTube video transcript summaries"""

    def __init__(self, api_key: str, model: str = "deepseek/deepseek-chat-v3.1:free", max_tokens: int = 500, enabled: bool = True):
        """
        Initialize YouTube enricher

        Args:
            api_key: OpenRouter API key for LLM summarization
            model: LLM model to use for summarization
            max_tokens: Maximum tokens for summary
            enabled: Whether this enricher is enabled
        """
        self.enabled = enabled
        self.model = model
        self.max_tokens = max_tokens
        self.prompt_loader = PromptLoader()

        if self.enabled:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key
            )
            logger.info(f"YouTubeEnricher initialized (enabled={enabled}, model={model})")
        else:
            self.client = None
            logger.info("YouTubeEnricher disabled")

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from URL

        Supports formats:
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID

        Args:
            url: YouTube URL

        Returns:
            Video ID or None if not a valid YouTube URL
        """
        # Pattern 1: youtu.be/VIDEO_ID
        pattern1 = r'youtu\.be/([a-zA-Z0-9_-]+)'
        match = re.search(pattern1, url)
        if match:
            return match.group(1)

        # Pattern 2: youtube.com/watch?v=VIDEO_ID
        pattern2 = r'[?&]v=([a-zA-Z0-9_-]+)'
        match = re.search(pattern2, url)
        if match:
            return match.group(1)

        # Pattern 3: youtube.com/embed/VIDEO_ID
        pattern3 = r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
        match = re.search(pattern3, url)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Check if URL is a YouTube video"""
        return bool(YouTubeEnricher.extract_video_id(url))

    def fetch_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch transcript for a YouTube video

        Args:
            video_id: YouTube video ID

        Returns:
            Full transcript text or None if unavailable
        """
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'zh-CN', 'zh-TW'])

            if not transcript_list:
                logger.warning(f"Empty transcript for video {video_id}")
                return None

            # Concatenate all text snippets
            full_text = " ".join([entry['text'] for entry in transcript_list])

            logger.info(f"Successfully fetched transcript for {video_id} ({len(full_text)} characters)")
            return full_text

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video {video_id}")
            return None
        except NoTranscriptFound:
            logger.warning(f"No transcript found for video {video_id}")
            return None
        except VideoUnavailable:
            logger.warning(f"Video {video_id} is unavailable")
            return None
        except Exception as e:
            logger.error(f"Error fetching transcript for {video_id}: {e}")
            return None

    def summarize_transcript(self, transcript: str, video_url: str) -> Optional[str]:
        """
        Generate summary of transcript using LLM

        Args:
            transcript: Full transcript text
            video_url: YouTube video URL (for context)

        Returns:
            Summary text or None if failed
        """
        if not self.client:
            logger.warning("YouTubeEnricher not initialized (disabled)")
            return None

        try:
            # Truncate transcript if too long (to avoid token limits)
            max_transcript_length = 100000  # ~25000 tokens
            if len(transcript) > max_transcript_length:
                transcript = transcript[:max_transcript_length] + "..."
                logger.info(f"Truncated transcript to {max_transcript_length} characters")

            # Generate prompt from template
            prompt = self.prompt_loader.get_youtube_summary_prompt(video_url, transcript)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3
            )

            summary = response.choices[0].message.content

            if not summary or len(summary.strip()) == 0:
                logger.warning(f"Empty summary returned for video {video_url}")
                return None

            logger.info(f"Successfully generated summary ({len(summary)} characters)")
            return summary.strip()

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None

    def enrich_post(self, post, existing_post: Optional[dict] = None):
        """
        Enrich a post with YouTube transcript summary if applicable

        Args:
            post: RedditPost object
            existing_post: Existing post from database (for caching)

        Returns:
            RedditPost object (with youtube_transcript_summary as extra attribute)
        """
        # Skip if enricher is disabled
        if not self.enabled:
            return post

        # Check if already have cached summary
        if existing_post and 'youtube_transcript_summary' in existing_post:
            post.youtube_transcript_summary = existing_post['youtube_transcript_summary']
            logger.info(f"Using cached YouTube summary for post {post.post_id}")
            return post

        # Check if URL is a YouTube video
        if not self.is_youtube_url(post.url):
            return post

        logger.info(f"Processing YouTube video: {post.url}")

        # Extract video ID
        video_id = self.extract_video_id(post.url)
        if not video_id:
            logger.warning(f"Failed to extract video ID from {post.url}")
            return post

        # Fetch transcript
        transcript = self.fetch_transcript(video_id)
        if not transcript:
            logger.info(f"No transcript available for {post.url}, skipping")
            return post

        # Generate summary
        summary = self.summarize_transcript(transcript, post.url)
        if not summary:
            logger.info(f"Failed to generate summary for {post.url}, skipping")
            return post

        # Success! Add to post as extra attribute
        post.youtube_transcript_summary = summary
        logger.info(f"Successfully enriched post {post.post_id} with YouTube summary")

        return post
