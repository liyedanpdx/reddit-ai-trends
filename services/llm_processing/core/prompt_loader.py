"""
Prompt Template Loader

This module provides functionality to load and render Jinja2 prompt templates.
"""

import os
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, Template
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """Loader for Jinja2 prompt templates."""

    def __init__(self):
        """Initialize the prompt loader with the prompts directory."""
        # Get the directory where this file is located (core/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to llm_processing/, then into prompts/
        llm_processing_dir = os.path.dirname(current_dir)
        prompts_dir = os.path.join(llm_processing_dir, "prompts")

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(prompts_dir),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )

        logger.info(f"PromptLoader initialized with prompts directory: {prompts_dir}")

    def load_template(self, template_name: str) -> Template:
        """
        Load a Jinja2 template by name.

        Args:
            template_name: Name of the template file (e.g., 'report_generation_en.j2')

        Returns:
            Jinja2 Template object
        """
        try:
            template = self.env.get_template(template_name)
            logger.debug(f"Template loaded successfully: {template_name}")
            return template
        except Exception as e:
            logger.error(f"Error loading template {template_name}: {e}")
            raise

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Load and render a Jinja2 template with the given context.

        Args:
            template_name: Name of the template file
            context: Dictionary of variables to pass to the template

        Returns:
            Rendered template as a string
        """
        template = self.load_template(template_name)
        try:
            rendered = template.render(**context)
            logger.debug(f"Template rendered successfully: {template_name}")
            return rendered
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise

    def get_report_prompt(self, language: str, context: Dict[str, Any]) -> str:
        """
        Get the report generation prompt for a specific language.

        Args:
            language: Language code ('en' or 'zh')
            context: Dictionary containing:
                - current_date: Date string for the report
                - trending_table: Markdown table of trending posts
                - weekly_table: Markdown table of weekly posts
                - monthly_table: Markdown table of monthly posts
                - community_tables: Markdown tables of community posts

        Returns:
            Rendered prompt string
        """
        template_name = f"report_generation_{language}.j2"
        return self.render_template(template_name, context)

    def get_youtube_summary_prompt(self, video_url: str, transcript: str) -> str:
        """
        Get the YouTube video transcript summarization prompt.

        Args:
            video_url: YouTube video URL
            transcript: Video transcript text

        Returns:
            Rendered prompt string
        """
        context = {
            "video_url": video_url,
            "transcript": transcript
        }
        return self.render_template("youtube_summary.j2", context)

    def get_web_content_summary_prompt(self, url: str, content: str) -> str:
        """
        Get the web content summarization prompt.

        Args:
            url: Web page URL
            content: Page content (markdown format)

        Returns:
            Rendered prompt string
        """
        context = {
            "url": url,
            "content": content
        }
        return self.render_template("web_content_summary.j2", context)

    def get_image_analysis_prompt(self) -> str:
        """
        Get the image analysis prompt.

        Returns:
            Rendered prompt string
        """
        return self.render_template("image_analysis.j2", {})


if __name__ == "__main__":
    """Simple test for PromptLoader."""
    print("=" * 60)
    print("Testing PromptLoader")
    print("=" * 60)

    try:
        # Initialize loader
        loader = PromptLoader()
        print("✓ PromptLoader initialized successfully")

        # Test context
        test_context = {
            "current_date": "2025-01-15",
            "trending_table": "| Title | Score |\n|-------|-------|\n| Test Post | 100 |",
            "weekly_table": "| Title | Score |\n|-------|-------|\n| Weekly Post | 200 |",
            "monthly_table": "| Title | Score |\n|-------|-------|\n| Monthly Post | 300 |",
            "community_tables": "| Community | Title |\n|-----------|-------|\n| r/test | Community Post |"
        }

        # Test English template
        print("\n📝 Testing English template...")
        en_prompt = loader.get_report_prompt("en", test_context)
        print(f"✓ English prompt rendered ({len(en_prompt)} characters)")
        print(f"\nFirst 200 characters:\n{en_prompt[:200]}...")

        # Test Chinese template
        print("\n📝 Testing Chinese template...")
        zh_prompt = loader.get_report_prompt("zh", test_context)
        print(f"✓ Chinese prompt rendered ({len(zh_prompt)} characters)")
        print(f"\nFirst 200 characters:\n{zh_prompt[:200]}...")

        print("\n" + "=" * 60)
        print("✓ PromptLoader test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
