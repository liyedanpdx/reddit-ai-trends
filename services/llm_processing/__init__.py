"""
LLM Processing Package

This package provides LLM client implementations and report processing functionality.

Structure:
- clients/: LLM client implementations (base, groq, openrouter)
- core/: Core utilities (factory, prompt_loader)
- prompts/: Jinja2 templates for prompts
- report_processor.py: Main report processing logic
"""

from services.llm_processing.core.factory import LLMClientFactory
from services.llm_processing.clients.base_client import BaseLLMClient
from services.llm_processing.report_processor import ReportProcessor

__all__ = [
    'LLMClientFactory',
    'BaseLLMClient',
    'ReportProcessor'
] 