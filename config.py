"""
Configuration file for Reddit Post Trend Analyzer
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Reddit communities to monitor
REDDIT_COMMUNITIES = {
    # High priority communities (fetch top 30 posts)
    "high_priority": {
        "LocalLLaMA": 30,
        "MachineLearning": 30,
        "singularity": 30
    },
    # Medium priority communities (fetch top 10 posts)
    "medium_priority": {
        "LocalLLM": 10,
        "hackernews": 10,
        "LangChain": 10,
        "LLMDevs": 10,
        "Vectordatabase": 10,
        "Rag": 10,
        "ai_agents": 10,
        "datascience": 10
    }
}

# LLM Provider Configuration
# Current active provider
CURRENT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()

# Provider configurations - all settings for each provider
LLM_PROVIDERS = {
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.4")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096"))
    },
    "openrouter": {
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "model": os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-r1-distill-llama-70b:free"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "1")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "4096"))
    }
}

# Legacy LLM_CONFIG for backward compatibility
LLM_CONFIG = LLM_PROVIDERS.get(CURRENT_LLM_PROVIDER, LLM_PROVIDERS["openrouter"])

# Reddit Data Collection Configuration (PRIMARY SOURCE)
REDDIT_COLLECTION_CONFIG = {
    # Comment fetching strategy (costs API calls)
    # Options: "true" (always), "false" (never), "smart" (auto-detect based on content)
    "fetch_comments": os.getenv("FETCH_COMMENTS", "smart").lower(),
    # Number of top comments to fetch per post
    "top_comments_limit": int(os.getenv("TOP_COMMENTS_LIMIT", "5")),
    # Minimum selftext length to skip comments (for smart mode)
    "min_selftext_length": int(os.getenv("MIN_SELFTEXT_LENGTH", "100")),
    # Whether to analyze images in posts (costs API calls to Gemini)
    "analyze_images": os.getenv("ANALYZE_IMAGES", "false").lower() == "true",
    # Posts per subreddit
    "posts_per_subreddit": int(os.getenv("POSTS_PER_SUBREDDIT", "30")),
    # Subreddits to monitor
    "subreddits": os.getenv("REDDIT_SUBREDDITS", "LocalLLaMA,MachineLearning,singularity,LocalLLM,hackernews,LangChain,LLMDevs,Vectordatabase,Rag,ai_agents,datascience").split(",")
}

# Report generation configuration
REPORT_CONFIG = {
    "frequency_hours": 24,
    "report_title_format": "Reddit AI Report - {date}",
    "report_title_format_zh": "Reddit AI 趋势报告 - {date}",
    "report_directory": "reports",
    "database_name": "reddit-report",
    "collections": {
        "posts": "posts",
        "reports": "reports"
    },
    # 从环境变量加载报告生成时间，默认为美国中部时间早上6点
    "generation_time": os.getenv("REPORT_GENERATION_TIME", "06:00"),
    # 支持的语言列表，默认为英文和中文
    "languages": os.getenv("REPORT_LANGUAGES", "en,zh").split(","),
    # Reference REDDIT_COLLECTION_CONFIG for these values (single source of truth)
    "posts_per_subreddit": REDDIT_COLLECTION_CONFIG["posts_per_subreddit"],
    "subreddits": REDDIT_COLLECTION_CONFIG["subreddits"]
}

# Post categories
POST_CATEGORIES = [
    "Technical Problem",
    "Technical Solution",
    "New Technology",
    "Large Language Model",
    "Application",
    "Best Practice",
    "Research",
    "Discussion",
    "News",
    "Other"
]

# 从环境变量加载要排除的类别
EXCLUDED_CATEGORIES = os.getenv("EXCLUDED_CATEGORIES", "").split(",")
# 移除空字符串
EXCLUDED_CATEGORIES = [cat.strip() for cat in EXCLUDED_CATEGORIES if cat.strip()]

# GitHub configuration
GITHUB_CONFIG = {
    "repo_name": "reddit-ai-report",
    "branch": "main",
    "commit_message_format": "Update report for {date}"
}

# Image Analysis Configuration (for Vision API settings)
IMAGE_ANALYSIS_CONFIG = {
    # Note: "enabled" is controlled by REDDIT_COLLECTION_CONFIG["analyze_images"]
    # Primary model to use
    "model": os.getenv("IMAGE_ANALYSIS_MODEL", "qwen/qwen2.5-vl-72b-instruct:free"),
    # Fallback models for automatic retry if primary fails (rate limit, downtime, etc.)
    "fallback_models": os.getenv(
        "IMAGE_ANALYSIS_FALLBACK_MODELS",
        "google/gemini-2.0-flash-exp:free,mistralai/mistral-small-3.2-24b-instruct:free,mistralai/mistral-small-3.1-24b-instruct:free,meta-llama/llama-4-maverick:free"
    ).split(","),
    "max_tokens": int(os.getenv("IMAGE_ANALYSIS_MAX_TOKENS", "500"))
}

# YouTube Transcript Analysis Configuration
YOUTUBE_ANALYSIS_CONFIG = {
    "enabled": os.getenv("YOUTUBE_ANALYSIS_ENABLED", "true").lower() == "true",
    "model": os.getenv("YOUTUBE_ANALYSIS_MODEL", "deepseek/deepseek-chat-v3.1:free"),
    "max_tokens": int(os.getenv("YOUTUBE_ANALYSIS_MAX_TOKENS", "500"))
}

# Web Content Analysis Configuration
WEB_CONTENT_ANALYSIS_CONFIG = {
    "enabled": os.getenv("WEB_CONTENT_ANALYSIS_ENABLED", "true").lower() == "true",
    "firecrawl_api_key": os.getenv("FIRECRAWL_API_KEY"),
    "model": os.getenv("WEB_CONTENT_ANALYSIS_MODEL", "deepseek/deepseek-chat-v3.1:free"),
    "max_tokens": int(os.getenv("WEB_CONTENT_ANALYSIS_MAX_TOKENS", "500"))
}

# Docker configuration
DOCKER_CONFIG = {
    "image_name": "reddit-ai-report",
    "container_name": "reddit-ai-report-container",
    "port": 8080
} 