# Reddit AI 趋势报告

[English](README.md) | [中文](README_CN.md)

自动从Reddit AI相关社区生成趋势报告，支持英文和中文双语。通过每日报告，随时了解AI领域的最新发展。

## 最新报告 (2026-02-20)

- [英文报告](reports/latest_report_en.md)
- [中文报告](reports/latest_report_zh.md)

## 功能特点

- **实时AI趋势监控**：实时跟踪新兴AI技术、讨论和突破性进展
- **多社区分析**：收集来自各种AI相关subreddit的数据，提供全面视图
- **多模态内容分析**：
  - 使用视觉模型（Qwen-VL、Gemini等）进行图片分析
  - YouTube视频字幕提取与总结
  - 通过Firecrawl进行网页内容抓取与总结
  - 社区评论集成与机器人过滤
- **详细趋势分析**：生成深入报告，包括今日焦点、周趋势对比、月度技术演进等
- **双语支持**：同时生成英文和中文报告
- **多LLM提供商**：支持Groq和OpenRouter API
- **智能缓存**：基于数据库的缓存机制，最小化API成本
- **有组织的文件结构**：按年/月/日存储报告，便于访问
- **自动README更新**：自动更新指向最新报告的链接
- **Docker部署**：简易容器化部署
- **MongoDB持久化**：存储所有数据用于历史分析

## 最新更新

### **2025-10-09**
- 新增YouTube视频字幕分析 - 自动提取和总结视频内容
- 新增网页内容分析，使用Firecrawl - 抓取和总结链接文章
- 两个新enricher均使用DeepSeek进行经济高效的总结，带有健壮的错误处理
- 为所有enrichment数据（图片、YouTube、网页内容）提供数据库缓存，最小化API成本
- 所有enrichment功能均可选，可通过.env配置

### **2025-10-05**
- 新增可选的视觉模型支持，用于分析Reddit帖子中的图片（Qwen-VL、Gemini，支持自动故障转移，可通过.env配置）
- 新增可选的社区评论集成，自动过滤机器人评论（可通过.env配置）
- 重构Reddit数据收集框架，采用Clean Architecture（fetchers、enrichers、filters）
- 新增图片描述和评论的数据库缓存，减少API调用
- 改进提示词结构，使用JSON格式提升清晰度

### **2025-10-03**
- 新增OpenRouter API支持，可访问数十种免费和付费模型（Gemini、DeepSeek、Qwen等）
- 优化代码结构，提升可维护性
- 将提示词提取到独立模板文件，便于自定义

## 目录结构

```
reports/
  ├── YYYY/           # 年份目录
  │   ├── MM/         # 月份目录
  │   │   ├── DD/     # 日期目录
  │   │   │   ├── report_YYYYMMDD_HHMMSS_en.md  # 英文报告
  │   │   │   └── report_YYYYMMDD_HHMMSS_zh.md  # 中文报告
  ├── latest_report_en.md  # 最新英文报告的符号链接
  └── latest_report_zh.md  # 最新中文报告的符号链接
```

## 安装与设置

### 前提条件

- Docker和Docker Compose
- Reddit API凭证
- LLM API密钥（Groq或OpenRouter）

### 环境变量设置

1. 复制`.env.example`文件为`.env`：

```bash
cp .env.example .env
```

2. 编辑`.env`文件，填入您的API密钥和其他配置：

```bash
# Reddit API凭证
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_reddit_user_agent

# MongoDB连接
MONGODB_URI=mongodb://mongodb:27017
MONGODB_DATABASE=reddit_trends

# LLM提供商（groq或openrouter）
LLM_PROVIDER=openrouter

# Groq API（如果使用Groq）
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# OpenRouter API（如果使用OpenRouter）
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=deepseek/deepseek-r1-distill-llama-70b:free

# LLM设置（应用于所有提供商）
LLM_TEMPERATURE=0.5
LLM_MAX_TOKENS=8192

# Reddit数据收集配置
# 评论获取策略（会消耗API调用）：
#   - "true": 始终获取所有帖子的评论
#   - "false": 从不获取评论
#   - "smart": 自动检测 - 仅对内容少/无文本的帖子获取评论（推荐）
FETCH_COMMENTS=smart
TOP_COMMENTS_LIMIT=5  # 每个帖子包含的热门评论数量
MIN_SELFTEXT_LENGTH=100  # smart模式下跳过评论的最小文本长度

# 图片分析（会调用视觉模型API）
ANALYZE_IMAGES=true  # 启用/禁用图片分析
IMAGE_ANALYSIS_MODEL=qwen/qwen2.5-vl-72b-instruct:free  # 主视觉模型
# 备用模型（逗号分隔） - 主模型失败时OpenRouter会自动重试
IMAGE_ANALYSIS_FALLBACK_MODELS=google/gemini-2.0-flash-exp:free,mistralai/mistral-small-3.2-24b-instruct:free,meta-llama/llama-4-maverick:free
IMAGE_ANALYSIS_MAX_TOKENS=500  # 图片描述的最大token数

# YouTube字幕分析（免费 - 使用youtube-transcript-api，仅总结时调用LLM API）
YOUTUBE_ANALYSIS_ENABLED=true  # 启用/禁用YouTube视频字幕分析
YOUTUBE_ANALYSIS_MODEL=deepseek/deepseek-chat-v3.1:free  # 用于总结的LLM模型
YOUTUBE_ANALYSIS_MAX_TOKENS=500  # 视频总结的最大token数

# 网页内容分析（Firecrawl提供每月500免费额度，总结时调用LLM API）
WEB_CONTENT_ANALYSIS_ENABLED=true  # 启用/禁用网页内容分析
FIRECRAWL_API_KEY=your_firecrawl_api_key  # 从firecrawl.dev获取免费API密钥（每月500额度）
WEB_CONTENT_ANALYSIS_MODEL=deepseek/deepseek-chat-v3.1:free  # 用于总结的LLM模型
WEB_CONTENT_ANALYSIS_MAX_TOKENS=500  # 网页内容总结的最大token数

POSTS_PER_SUBREDDIT=30  # 每个subreddit获取的帖子数量
REDDIT_SUBREDDITS=LocalLLaMA,MachineLearning,singularity,LocalLLM,hackernews,LangChain,LLMDevs,Vectordatabase,Rag,ai_agents,datascience

# 报告生成设置
REPORT_GENERATION_TIME=06:00
REPORT_LANGUAGES=en,zh
```

**注意**：OpenRouter提供数十种LLM模型，包括免费选项（DeepSeek、Gemini、Qwen）和付费模型。在 [openrouter.ai](https://openrouter.ai) 获取API密钥

## 使用方法

### 使用Docker Compose部署

1. 构建并启动容器：

```bash
docker-compose up -d
```

2. 查看日志：

```bash
docker-compose logs -f app
```

### 手动运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 生成一次性报告：

```bash
python report_generation.py --languages en zh
```

3. 设置定时生成报告：

```bash
python report_generation.py --interval 24
```

## 创建GitHub仓库

1. 在GitHub上创建一个新仓库

2. 初始化本地仓库并推送：

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/reddit-ai-trends.git
git push -u origin main
```

## 自定义配置

您可以在`config.py`文件中修改以下配置：

- 要监控的subreddit列表
- 每个subreddit要获取的帖子数量
- 报告生成时间
- 支持的语言
- LLM模型参数

## AI趋势监控

该系统旨在通过以下方式让您了解AI领域的最新发展：

- 实时跟踪新兴技术和突破性进展
- 识别不同AI社区的热门话题
- 将当前趋势与历史数据比较以发现新兴模式
- 突出小型社区中可能被忽视的独特讨论
- 对特别有趣或重要的趋势提供技术深度分析

每日报告为您提供AI世界正在发生的事情的全面视图，帮助您保持领先地位并在它们出现时识别重要发展。

## 故障排除

- **报告未生成**：检查API密钥是否正确，以及日志中是否有错误信息
- **MongoDB连接失败**：确保MongoDB服务正在运行，并且连接URI正确
- **符号链接不工作**：在Windows系统上，可能需要管理员权限来创建符号链接

## 许可证

MIT 