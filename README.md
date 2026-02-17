# Reddit AI Trend Reports

[English](README.md) | [中文](README_CN.md)

Automatically generate trend reports from AI-related Reddit communities, supporting both English and Chinese languages. Stay up-to-date with the latest developments in the AI field through daily reports.

## Latest Reports (2026-02-17)

- [English Report](reports/latest_report_en.md)
- [Chinese Report](reports/latest_report_zh.md)

## Features

- **Real-time AI Trend Monitoring**: Track emerging AI technologies, discussions, and breakthroughs as they happen
- **Multi-community Analysis**: Collect data from various AI-related subreddits to provide a comprehensive view
- **Multimodal Content Analysis**:
  - Image analysis using vision models (Qwen-VL, Gemini, etc.)
  - YouTube video transcript extraction and summarization
  - Web page content scraping and summarization via Firecrawl
  - Community comment integration with bot filtering
- **Detailed Trend Analysis**: Generate in-depth reports including today's highlights, weekly trend comparisons, monthly technology evolution, and more
- **Bilingual Support**: Generate reports in both English and Chinese
- **Multiple LLM Providers**: Supports both Groq and OpenRouter APIs
- **Smart Caching**: Database-backed caching for all enrichments to minimize API costs
- **Organized File Structure**: Store reports in year/month/day folders for easy access
- **Automatic README Updates**: Automatically update links to the latest reports
- **Docker Deployment**: Easy containerized deployment
- **MongoDB Persistence**: Store all data for historical analysis

## Recent Updates

### **2025-10-09**
- Added YouTube video transcript analysis - automatically extracts and summarizes video content
- Added web page content analysis using Firecrawl - scrapes and summarizes linked articles
- Both new enrichers use DeepSeek for cost-effective summarization with robust error handling
- Database caching for all enrichment data (images, YouTube, web content) to minimize API costs
- All enrichment features are optional and configurable via .env

### **2025-10-05**
- Added optional vision model support for analyzing images in Reddit posts (Qwen-VL, Gemini with automatic fallback, configurable via .env)
- Added optional community comments integration with automatic bot filtering (configurable via .env)
- Refactored Reddit collection framework with Clean Architecture (fetchers, enrichers, filters)
- Added database caching for image descriptions and comments to reduce API calls
- Improved prompt structure with JSON format for better clarity

### **2025-10-03**
- Added OpenRouter API support with access to dozens of free and paid models (Gemini, DeepSeek, Qwen, etc.)
- Improved code organization for better maintainability
- Extracted prompts into separate template files for easier customization

## Directory Structure

```
reports/
  ├── YYYY/           # Year directory
  │   ├── MM/         # Month directory
  │   │   ├── DD/     # Day directory
  │   │   │   ├── report_YYYYMMDD_HHMMSS_en.md  # English report
  │   │   │   └── report_YYYYMMDD_HHMMSS_zh.md  # Chinese report
  ├── latest_report_en.md  # Symlink to latest English report
  └── latest_report_zh.md  # Symlink to latest Chinese report
```

## Installation and Setup

### Prerequisites

- Docker and Docker Compose
- Reddit API credentials
- LLM API key (Groq or OpenRouter)

### Environment Variables Setup

1. Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

2. Edit the `.env` file with your API keys and other configurations:

```bash
# Reddit API credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent

# MongoDB connection
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=reddit_trends

# LLM Provider (groq or openrouter)
LLM_PROVIDER=openrouter

# Groq API (if using Groq)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# OpenRouter API (if using OpenRouter)
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=deepseek/deepseek-r1-distill-llama-70b:free

# LLM Settings (applies to all providers)
LLM_TEMPERATURE=0.5
LLM_MAX_TOKENS=8192

# Reddit Data Collection Configuration
# Comment fetching strategy (costs API calls):
#   - "true": Always fetch comments for all posts
#   - "false": Never fetch comments
#   - "smart": Auto-detect - fetch only for posts with little/no text content (RECOMMENDED)
FETCH_COMMENTS=smart
TOP_COMMENTS_LIMIT=5  # Number of top comments to include per post
MIN_SELFTEXT_LENGTH=100  # Minimum text length to skip comments in smart mode

# Image Analysis (costs API calls to vision models)
ANALYZE_IMAGES=true  # Enable/disable image analysis
IMAGE_ANALYSIS_MODEL=qwen/qwen2.5-vl-72b-instruct:free  # Primary vision model
# Fallback models (comma-separated) - OpenRouter will auto-retry if primary fails
IMAGE_ANALYSIS_FALLBACK_MODELS=google/gemini-2.0-flash-exp:free,mistralai/mistral-small-3.2-24b-instruct:free,meta-llama/llama-4-maverick:free
IMAGE_ANALYSIS_MAX_TOKENS=500  # Max tokens for image descriptions

# YouTube Transcript Analysis (FREE - uses youtube-transcript-api, only costs LLM API for summarization)
YOUTUBE_ANALYSIS_ENABLED=true  # Enable/disable YouTube video transcript analysis
YOUTUBE_ANALYSIS_MODEL=deepseek/deepseek-chat-v3.1:free  # LLM model for summarization
YOUTUBE_ANALYSIS_MAX_TOKENS=500  # Max tokens for video summaries

# Web Content Analysis (Firecrawl offers 500 free credits/month, also costs LLM API for summarization)
WEB_CONTENT_ANALYSIS_ENABLED=true  # Enable/disable web page content analysis
FIRECRAWL_API_KEY=your_firecrawl_api_key  # Get free API key from firecrawl.dev (500 credits/month free)
WEB_CONTENT_ANALYSIS_MODEL=deepseek/deepseek-chat-v3.1:free  # LLM model for summarization
WEB_CONTENT_ANALYSIS_MAX_TOKENS=500  # Max tokens for web content summaries

POSTS_PER_SUBREDDIT=30  # Number of posts to fetch per subreddit
REDDIT_SUBREDDITS=LocalLLaMA,MachineLearning,singularity,LocalLLM,hackernews,LangChain,LLMDevs,Vectordatabase,Rag,ai_agents,datascience

# Report generation settings
REPORT_GENERATION_TIME=06:00
REPORT_LANGUAGES=en,zh
```

**Note**: OpenRouter provides access to dozens of LLM models including free options (DeepSeek, Gemini, Qwen) and paid models. Get your API key at [openrouter.ai](https://openrouter.ai)

## Usage

### Deploy with Docker Compose

1. Build and start the containers:

```bash
docker-compose up -d
```

2. View the logs:

```bash
docker-compose logs -f app
```

### Run Manually

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Generate a one-time report:

```bash
python report_generation.py --languages en zh
```

3. Set up scheduled report generation:

```bash
python report_generation.py --interval 24
```

## Creating a GitHub Repository

1. Create a new repository on GitHub

2. Initialize your local repository and push:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/reddit-ai-trends.git
git push -u origin main
```

## Custom Configuration

You can modify the following configurations in the `config.py` file:

- List of subreddits to monitor
- Number of posts to fetch per subreddit
- Report generation time
- Supported languages
- LLM model parameters

## AI Trend Monitoring

This system is designed to keep you informed about the latest developments in the AI field by:

- Tracking emerging technologies and breakthroughs in real-time
- Identifying trending topics across different AI communities
- Comparing current trends with historical data to spot emerging patterns
- Highlighting unique discussions from smaller communities that might be overlooked
- Providing technical deep dives into particularly interesting or important trends

The daily reports give you a comprehensive view of what's happening in the AI world, helping you stay ahead of the curve and identify important developments as they emerge.

## Troubleshooting

- **Reports not generating**: Check if your API keys are correct and look for error messages in the logs
- **MongoDB connection failing**: Ensure MongoDB service is running and the connection URI is correct
- **Symlinks not working**: On Windows systems, you may need administrator privileges to create symlinks

## License

MIT