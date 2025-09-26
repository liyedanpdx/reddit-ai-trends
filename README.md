# Reddit AI Trend Reports

[English](README.md) | [中文](README_CN.md)

Automatically generate trend reports from AI-related Reddit communities, supporting both English and Chinese languages. Stay up-to-date with the latest developments in the AI field through daily reports.

## Latest Reports (2025-09-26)

- [English Report](reports/latest_report_en.md)
- [Chinese Report](reports/latest_report_zh.md)

## Features

- **Real-time AI Trend Monitoring**: Track emerging AI technologies, discussions, and breakthroughs as they happen
- **Multi-community Analysis**: Collect data from various AI-related subreddits to provide a comprehensive view
- **Detailed Trend Analysis**: Generate in-depth reports including today's highlights, weekly trend comparisons, monthly technology evolution, and more
- **Bilingual Support**: Generate reports in both English and Chinese
- **Organized File Structure**: Store reports in year/month/day folders for easy access
- **Automatic README Updates**: Automatically update links to the latest reports
- **Docker Deployment**: Easy containerized deployment
- **MongoDB Persistence**: Store all data for historical analysis

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
- Groq API key

### Environment Variables Setup

1. Copy the `.env.example` file to `.env`:

```bash
cp .env.example .env
```

2. Edit the `.env` file with your API keys and other configurations:

```
# Reddit API credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent

# MongoDB connection
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=reddit_trends

# Groq API key
GROQ_API_KEY=your_groq_api_key

# Report generation settings
REPORT_GENERATION_TIME=06:00
REPORT_LANGUAGES=en,zh
```

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