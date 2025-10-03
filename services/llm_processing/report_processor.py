"""
Report Processor

This module provides functionality to process and format Reddit reports.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import markdown
from services.llm_processing.core.factory import LLMClientFactory
from config import REPORT_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReportProcessor:
    """Service for processing and formatting Reddit reports."""
    
    def __init__(self):
        """Initialize the report processor."""
        self.llm_client = LLMClientFactory.create_client()
        logger.info("Report processor initialized")
    
    def generate_report(self, 
                       posts: List[Dict[str, Any]], 
                       previous_report: Optional[Dict[str, Any]] = None,
                       weekly_posts: Optional[List[Dict[str, Any]]] = None,
                       monthly_posts: Optional[List[Dict[str, Any]]] = None,
                       language: str = "en",
                       reference_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Generate a report based on Reddit posts.
        
        Args:
            posts: List of post dictionaries
            previous_report: Optional previous report for comparison
            weekly_posts: List of weekly popular posts
            monthly_posts: List of monthly popular posts
            language: Language for the report ('en' for English, 'zh' for Chinese)
            reference_date: Optional specific date to generate report for (defaults to current date)
            
        Returns:
            Report dictionary
        """
        logger.info(f"Generating report based on {len(posts)} posts in {language} language")
        
        # Generate the report content using the LLM
        markdown_content = self.llm_client.generate_report(
            posts, 
            previous_report, 
            weekly_posts, 
            monthly_posts,
            language=language,
            reference_date=reference_date
        )
        
        # Create the report object
        timestamp = reference_date if reference_date is not None else datetime.utcnow()
        
        # Set language-specific title format
        if language == "zh":
            title_format = REPORT_CONFIG.get('report_title_format_zh', "Reddit AI 趋势报告 - {date}")
        else:
            title_format = REPORT_CONFIG.get('report_title_format', "Reddit AI Trend Report - {date}")
        
        report = {
            "report_id": f"report_{timestamp.strftime('%Y%m%d_%H%M%S')}_{language}",
            "timestamp": timestamp,
            "language": language,
            "title": title_format.format(date=timestamp.strftime('%Y-%m-%d %H:%M UTC')),
            "content": markdown_content,
            "post_count": len(posts),
            "post_ids": [post.get('post_id') for post in posts if post.get('post_id')],
            "subreddits": list(set(post.get('subreddit') for post in posts if post.get('subreddit'))),
            "html_content": markdown.markdown(markdown_content)
        }
        
        logger.info(f"Report generated with ID: {report['report_id']} in {language} language")
        return report
    
    def generate_multilingual_reports(self,
                                     posts: List[Dict[str, Any]],
                                     previous_report: Optional[Dict[str, Any]] = None,
                                     weekly_posts: Optional[List[Dict[str, Any]]] = None,
                                     monthly_posts: Optional[List[Dict[str, Any]]] = None,
                                     languages: List[str] = ["en", "zh"],
                                     save_to_file: bool = True,
                                     reference_date: Optional[datetime] = None) -> Dict[str, Dict[str, Any]]:
        """
        Generate reports in multiple languages.
        
        Args:
            posts: List of post dictionaries
            previous_report: Optional previous report for comparison
            weekly_posts: List of weekly popular posts
            monthly_posts: List of monthly popular posts
            languages: List of language codes to generate reports for
            save_to_file: Whether to save the reports to files
            reference_date: Optional specific date to generate report for (defaults to current date)
            
        Returns:
            Dictionary mapping language codes to report dictionaries
        """
        reports = {}
        
        for lang in languages:
            logger.info(f"Generating report in {lang} language")
            report = self.generate_report(
                posts, 
                previous_report, 
                weekly_posts, 
                monthly_posts, 
                language=lang,
                reference_date=reference_date
            )
            reports[lang] = report
            
            # 如果需要保存到文件，则调用save_report_to_file方法
            if save_to_file:
                self.save_report_to_file(report)
            
        return reports
    
    def save_report_to_file(self, report: Dict[str, Any]) -> str:
        """
        Save a report to a file.
        
        Args:
            report: Report dictionary
            
        Returns:
            Path to the saved file
        """
        # Create the reports directory structure
        timestamp = report.get('timestamp', datetime.utcnow())
        year_month = timestamp.strftime('%Y-%m')
        week = f"week-{timestamp.strftime('%U')}"
        
        # Get language code for filename
        language = report.get('language', 'en')
        
        # Create directory structure: reports/YYYY-MM/week-WW/
        report_dir = os.path.join(REPORT_CONFIG['report_directory'], year_month, week)
        os.makedirs(report_dir, exist_ok=True)
        
        # Create the report filename with language code
        filename = f"report_{timestamp.strftime('%Y%m%d_%H%M%S')}_{language}.md"
        filepath = os.path.join(report_dir, filename)
        
        # Save the report content to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report['content'])
        
        logger.info(f"Report saved to file: {filepath}")
        
        # Also save metadata
        metadata_filename = f"report_{timestamp.strftime('%Y%m%d_%H%M%S')}_{language}_metadata.json"
        metadata_filepath = os.path.join(report_dir, metadata_filename)
        
        # Create metadata object (excluding large content fields)
        metadata = {
            "report_id": report.get('report_id'),
            "timestamp": report.get('timestamp').isoformat() if isinstance(report.get('timestamp'), datetime) else report.get('timestamp'),
            "language": language,
            "title": report.get('title'),
            "post_count": report.get('post_count'),
            "post_ids": report.get('post_ids'),
            "subreddits": report.get('subreddits'),
            "filepath": filepath
        }
        
        # Save metadata
        with open(metadata_filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info(f"Report metadata saved to file: {metadata_filepath}")
        
        return filepath
        
    def save_multilingual_reports_to_files(self, reports: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """
        Save multiple language reports to files.
        
        Args:
            reports: Dictionary mapping language codes to report dictionaries
            
        Returns:
            Dictionary mapping language codes to file paths
        """
        filepaths = {}
        
        for lang, report in reports.items():
            filepath = self.save_report_to_file(report)
            filepaths[lang] = filepath
            
        return filepaths 