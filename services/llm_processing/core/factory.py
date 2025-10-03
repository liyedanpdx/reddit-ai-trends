"""
LLM Client Factory

This module provides a factory for creating LLM client instances based on configuration.
"""

import os
import logging
from dotenv import load_dotenv
from services.llm_processing.clients.base_client import BaseLLMClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LLMClientFactory:
    """Factory class for creating LLM client instances."""

    @staticmethod
    def create_client() -> BaseLLMClient:
        """
        Create an LLM client based on the LLM_PROVIDER environment variable.

        Returns:
            An instance of BaseLLMClient (either GroqClient or OpenRouterClient)

        Raises:
            ValueError: If the LLM_PROVIDER is not recognized
        """
        provider = os.getenv('LLM_PROVIDER', 'openrouter').lower()

        logger.info(f"Creating LLM client for provider: {provider}")

        if provider == 'groq':
            from services.llm_processing.clients.groq_client import GroqClient
            return GroqClient()
        elif provider == 'openrouter':
            from services.llm_processing.clients.openrouter_client import OpenRouterClient
            return OpenRouterClient()
        else:
            raise ValueError(
                f"Unknown LLM provider: {provider}. "
                f"Supported providers are: 'groq', 'openrouter'"
            )

    @staticmethod
    def get_available_providers():
        """
        Get a list of available LLM providers.

        Returns:
            List of provider names
        """
        return ['groq', 'openrouter']
