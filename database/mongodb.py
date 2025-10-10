
"""
MongoDB Client Module

This module provides functionality to interact with MongoDB for storing and retrieving Reddit data.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
from config import REPORT_CONFIG

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MongoDBClient:
    """Client for interacting with MongoDB."""
    
    def __init__(self):
        """Initialize the MongoDB client using credentials from environment variables."""
        self.connection_string = os.getenv('MONGODB_CONNECTION_STRING')
        if not self.connection_string:
            raise ValueError("MongoDB connection string not found in environment variables")
        
        self.client = MongoClient(self.connection_string)
        self.db = self.client[REPORT_CONFIG['database_name']]
        self.posts_collection = self.db[REPORT_CONFIG['collections']['posts']]
        self.reports_collection = self.db[REPORT_CONFIG['collections']['reports']]
        
        # Create indexes for better performance
        self._create_indexes()
        
        logger.info(f"Connected to MongoDB database: {REPORT_CONFIG['database_name']}")
    
    def _create_indexes(self):
        """Create indexes for better query performance."""
        # Create index on post_id for faster lookups
        self.posts_collection.create_index("post_id", unique=True)

        # Create index on subreddit for faster filtering
        self.posts_collection.create_index("subreddit")

        # Create index on created_utc for faster time-based queries
        self.posts_collection.create_index("created_utc")

        # Create index on report_id for faster lookups
        self.reports_collection.create_index("report_id", unique=True)

        # Create index on timestamp for faster time-based queries
        self.reports_collection.create_index("timestamp")

    def _merge_comments(self, existing_comments: List[Dict[str, Any]], new_comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Intelligently merge new comments with existing comments.

        Strategy:
        - Preserve existing comments and their history
        - Update scores for comments that still appear in top 5
        - Add new comments that entered top 5
        - Mark comments that dropped out of top 5 as historical

        Args:
            existing_comments: List of existing comment dictionaries from database
            new_comments: List of newly fetched comment dictionaries

        Returns:
            Merged list of comments with updated metadata and score history
        """
        if not existing_comments:
            # No existing comments, initialize new ones with metadata
            now = datetime.utcnow()
            for comment in new_comments:
                comment['first_seen'] = now
                comment['last_updated'] = now
                comment['score_history'] = [{'timestamp': now, 'score': comment.get('score', 0)}]
            return new_comments

        if not new_comments:
            # No new comments fetched, return existing (happens when fetch_comments is skipped)
            return existing_comments

        # Create index of existing comments by comment_id
        existing_by_id = {c['comment_id']: c for c in existing_comments if 'comment_id' in c}

        merged = []
        now = datetime.utcnow()
        new_comment_ids = set()

        # Process new comments
        for new_comment in new_comments:
            comment_id = new_comment.get('comment_id')
            if not comment_id:
                logger.warning("Comment missing comment_id, skipping")
                continue

            new_comment_ids.add(comment_id)

            if comment_id in existing_by_id:
                # Comment already exists - update it
                old_comment = existing_by_id[comment_id].copy()

                # Initialize score_history if not present
                if 'score_history' not in old_comment:
                    old_comment['score_history'] = []

                # Add new score to history (only if score changed)
                new_score = new_comment.get('score', 0)
                old_score = old_comment.get('score', 0)

                if new_score != old_score:
                    old_comment['score_history'].append({
                        'timestamp': now,
                        'score': new_score
                    })

                    # Limit history to last 10 entries
                    if len(old_comment['score_history']) > 10:
                        old_comment['score_history'] = old_comment['score_history'][-10:]

                # Update current data
                old_comment['score'] = new_score
                old_comment['body'] = new_comment.get('body', old_comment.get('body', ''))
                old_comment['last_updated'] = now

                # Remove historical flag if it was previously marked
                old_comment.pop('historical', None)

                merged.append(old_comment)
            else:
                # New comment entering top 5
                new_comment['first_seen'] = now
                new_comment['last_updated'] = now
                new_comment['score_history'] = [{'timestamp': now, 'score': new_comment.get('score', 0)}]
                merged.append(new_comment)

        # Preserve comments that dropped out of top 5 (mark as historical)
        for comment_id, old_comment in existing_by_id.items():
            if comment_id not in new_comment_ids and not old_comment.get('historical', False):
                # Comment no longer in top 5, but keep it for historical tracking
                old_comment['historical'] = True
                old_comment['dropped_from_top'] = now
                merged.append(old_comment)

        # Sort: current top comments first (by score desc), then historical comments
        merged.sort(key=lambda c: (c.get('historical', False), -c.get('score', 0)))

        # Limit total comments to avoid database bloat (keep top 5 + last 10 historical)
        current_comments = [c for c in merged if not c.get('historical', False)]
        historical_comments = [c for c in merged if c.get('historical', False)][:10]

        return current_comments + historical_comments
    
    def insert_or_update_posts(self, posts: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Insert or update multiple posts in the database.
        
        Args:
            posts: List of post dictionaries
            
        Returns:
            Dictionary with counts of inserted and updated posts
        """
        if not posts:
            return {"inserted": 0, "updated": 0}
        
        # Prepare bulk operations
        operations = []
        for post in posts:
            # Use post_id as the unique identifier
            filter_query = {"post_id": post["post_id"]}
            
            # Add last_updated timestamp
            post["last_updated"] = datetime.utcnow()
            
            # Store previous metrics for comparison if the post already exists
            existing_post = self.posts_collection.find_one(filter_query)
            if existing_post:
                # Store historical metrics
                if "historical_metrics" not in post:
                    post["historical_metrics"] = []

                # Add current metrics to historical data
                if "historical_metrics" in existing_post:
                    post["historical_metrics"] = existing_post["historical_metrics"]

                # Add new historical entry
                historical_entry = {
                    "timestamp": datetime.utcnow(),
                    "score": existing_post.get("score", 0),
                    "num_comments": existing_post.get("num_comments", 0)
                }
                post["historical_metrics"].append(historical_entry)

                # Limit historical entries to last 10
                if len(post["historical_metrics"]) > 10:
                    post["historical_metrics"] = post["historical_metrics"][-10:]

                # Preserve enrichment fields if they exist (don't overwrite with new data)
                if "photo_parse" in existing_post:
                    post["photo_parse"] = existing_post["photo_parse"]
                if "youtube_transcript_summary" in existing_post:
                    post["youtube_transcript_summary"] = existing_post["youtube_transcript_summary"]
                if "web_content_summary" in existing_post:
                    post["web_content_summary"] = existing_post["web_content_summary"]

                # Intelligently merge comments
                existing_comments = existing_post.get("comments", [])
                new_comments = post.get("comments", [])

                if new_comments:
                    # New comments fetched - merge with existing
                    post["comments"] = self._merge_comments(existing_comments, new_comments)
                    post["comments_last_fetched"] = datetime.utcnow()
                elif existing_comments:
                    # No new comments fetched, preserve existing
                    post["comments"] = existing_comments
                    # Keep the old comments_last_fetched timestamp if it exists
                    if "comments_last_fetched" in existing_post:
                        post["comments_last_fetched"] = existing_post["comments_last_fetched"]
            
            # Create update operation
            operation = UpdateOne(
                filter_query,
                {"$set": post},
                upsert=True
            )
            operations.append(operation)
        
        try:
            # Execute bulk operations
            result = self.posts_collection.bulk_write(operations)
            
            # Return counts
            return {
                "inserted": result.upserted_count,
                "updated": result.modified_count
            }
        except PyMongoError as e:
            logger.error(f"Error inserting or updating posts: {e}")
            raise
    
    def get_posts_by_subreddit(self, subreddit: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get posts from a specific subreddit.
        
        Args:
            subreddit: Name of the subreddit
            limit: Maximum number of posts to return
            
        Returns:
            List of post dictionaries
        """
        try:
            cursor = self.posts_collection.find(
                {"subreddit": subreddit}
            ).sort("created_utc", -1).limit(limit)
            
            return list(cursor)
        except PyMongoError as e:
            logger.error(f"Error getting posts from subreddit {subreddit}: {e}")
            raise
    
    def get_posts_by_time_range(self, 
                               start_time: datetime, 
                               end_time: datetime, 
                               subreddit: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get posts within a specific time range.
        
        Args:
            start_time: Start time
            end_time: End time
            subreddit: Optional subreddit filter
            
        Returns:
            List of post dictionaries
        """
        query = {
            "created_utc": {
                "$gte": start_time,
                "$lte": end_time
            }
        }
        
        if subreddit:
            query["subreddit"] = subreddit
        
        try:
            cursor = self.posts_collection.find(query).sort("created_utc", -1)
            return list(cursor)
        except PyMongoError as e:
            logger.error(f"Error getting posts by time range: {e}")
            raise
    
    def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a post by its ID.
        
        Args:
            post_id: Post ID
            
        Returns:
            Post dictionary or None if not found
        """
        try:
            return self.posts_collection.find_one({"post_id": post_id})
        except PyMongoError as e:
            logger.error(f"Error getting post by ID {post_id}: {e}")
            raise
    
    def get_post_metrics_history(self, post_id: str) -> List[Dict[str, Any]]:
        """
        Get the metrics history for a specific post.
        
        Args:
            post_id: Post ID
            
        Returns:
            List of historical metrics or empty list if not found
        """
        try:
            post = self.posts_collection.find_one(
                {"post_id": post_id},
                {"historical_metrics": 1}
            )
            
            if post and "historical_metrics" in post:
                return post["historical_metrics"]
            
            return []
        except PyMongoError as e:
            logger.error(f"Error getting metrics history for post {post_id}: {e}")
            return []
    
    def insert_report(self, report: Dict[str, Any]) -> str:
        """
        Insert a new report.
        
        Args:
            report: Report dictionary
            
        Returns:
            ID of the inserted report
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in report:
                report["timestamp"] = datetime.utcnow()
            
            # Insert report
            result = self.reports_collection.insert_one(report)
            
            return str(result.inserted_id)
        except PyMongoError as e:
            logger.error(f"Error inserting report: {e}")
            raise
    
    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest report.
        
        Returns:
            Latest report dictionary or None if no reports exist
        """
        try:
            return self.reports_collection.find_one(
                sort=[("timestamp", -1)]
            )
        except PyMongoError as e:
            logger.error(f"Error getting latest report: {e}")
            raise
    
    def get_reports_by_time_range(self, 
                                 start_time: datetime, 
                                 end_time: datetime) -> List[Dict[str, Any]]:
        """
        Get reports within a specific time range.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            List of report dictionaries
        """
        try:
            cursor = self.reports_collection.find({
                "timestamp": {
                    "$gte": start_time,
                    "$lte": end_time
                }
            }).sort("timestamp", -1)
            
            return list(cursor)
        except PyMongoError as e:
            logger.error(f"Error getting reports by time range: {e}")
            raise
    
    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def get_posts_by_date_range(self, start_date: datetime, end_date: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取指定日期范围内的帖子。
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回的最大帖子数量
            
        Returns:
            帖子列表
        """
        try:
            # 将日期转换为Unix时间戳
            start_timestamp = start_date.timestamp()
            end_timestamp = end_date.timestamp()
            
            # 查询指定日期范围内的帖子
            query = {
                "created_utc": {
                    "$gte": start_timestamp,
                    "$lte": end_timestamp
                }
            }
            
            # 执行查询
            posts = list(self.posts_collection.find(query).limit(limit))
            
            logger.info(f"从MongoDB获取了 {len(posts)} 个日期范围内的帖子")
            return posts
        
        except PyMongoError as e:
            logger.error(f"获取日期范围内的帖子时出错: {e}")
            return []
    
    def get_latest_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最新的帖子。
        
        Args:
            limit: 返回的最大帖子数量
            
        Returns:
            帖子列表
        """
        try:
            # 按创建时间降序排序，获取最新的帖子
            posts = list(self.posts_collection.find().sort("created_utc", -1).limit(limit))
            
            logger.info(f"从MongoDB获取了 {len(posts)} 个最新帖子")
            return posts
        
        except PyMongoError as e:
            logger.error(f"获取最新帖子时出错: {e}")
            return []
    
    def get_latest_report_before_date(self, date: datetime) -> Optional[Dict[str, Any]]:
        """
        获取指定日期之前的最新报告。
        
        Args:
            date: 日期
            
        Returns:
            报告字典，如果没有找到则返回None
        """
        try:
            # 查询指定日期之前的最新报告
            query = {
                "created_at": {
                    "$lt": date.isoformat()
                }
            }
            
            # 按创建时间降序排序，获取最新的报告
            report = self.reports_collection.find_one(query, sort=[("created_at", -1)])
            
            if report:
                logger.info(f"找到了日期 {date.isoformat()} 之前的最新报告，ID: {report.get('report_id')}")
            else:
                logger.info(f"没有找到日期 {date.isoformat()} 之前的报告")
            
            return report
        
        except PyMongoError as e:
            logger.error(f"获取日期之前的最新报告时出错: {e}")
            return None
    
    def save_report(self, reports: Dict[str, Any], posts: List[Dict[str, Any]], 
                  weekly_posts: List[Dict[str, Any]], monthly_posts: List[Dict[str, Any]]) -> str:
        """
        保存报告数据到MongoDB，包括报告内容和帖子数据。
        
        Args:
            reports: 报告字典，键为语言代码，值为报告内容
            posts: 帖子列表
            weekly_posts: 每周热门帖子列表
            monthly_posts: 每月热门帖子列表
            
        Returns:
            报告ID
        """
        try:
            # 创建报告数据
            report_data = {
                "report_id": f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.utcnow(),
                "reports": reports,
                "posts_data": posts,
                "weekly_posts": weekly_posts,
                "monthly_posts": monthly_posts
            }
            
            # 插入报告数据
            result = self.reports_collection.insert_one(report_data)
            report_id = str(result.inserted_id)
            
            logger.info(f"保存报告数据到MongoDB，ID: {report_id}")
            return report_id
        
        except PyMongoError as e:
            logger.error(f"保存报告数据到MongoDB失败: {e}")
            raise 
