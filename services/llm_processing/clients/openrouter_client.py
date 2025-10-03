"""
OpenRouter API Client

This module provides functionality to interact with the OpenRouter API for LLM processing.
"""

import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config import LLM_PROVIDERS
from services.llm_processing.clients.base_client import BaseLLMClient, retry_on_empty_response

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OpenRouterClient(BaseLLMClient):
    """Client for interacting with the OpenRouter API."""

    def __init__(self):
        """Initialize the OpenRouter API client using credentials from config."""
        super().__init__()

        # Get OpenRouter config
        config = LLM_PROVIDERS.get("openrouter", {})

        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found in configuration")
        
        print(self.api_key)
        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

        # Get settings from config
        self.model = config.get("model", "deepseek/deepseek-r1-distill-llama-70b:free")
        self.temperature = config.get("temperature", 0.4)
        self.max_tokens = config.get("max_tokens", 4000)

        logger.info(f"OpenRouter API client initialized with model: {self.model}")

    @retry_on_empty_response(max_retries=10, retry_delay=10)
    def generate_text(self,
                     prompt: str,
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None) -> str:
        """
        Generate text using the OpenRouter API.

        Args:
            prompt: The prompt to send to the model
            temperature: Optional temperature override
            max_tokens: Optional max tokens override

        Returns:
            Generated text
        """
        # Use provided parameters or defaults
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        logger.info(f"Generating text with model: {self.model}, temperature: {temp}, max_tokens: {tokens}")

        # Call the OpenRouter API via OpenAI SDK
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides accurate and factual information."},
                {"role": "user", "content": prompt}
            ],
            temperature=temp,
            max_tokens=tokens,
            extra_body={}  # OpenRouter specific parameter
        )

        # Extract the generated text
        generated_text = response.choices[0].message.content

        # Clean the response using base class method
        generated_text = self._clean_response(generated_text) if generated_text else ""

        logger.info(f"Successfully generated text ({len(generated_text)} chars)")
        return generated_text


if __name__ == "__main__":
    """Simple test for OpenRouter client."""
    print("=" * 60)
    print("Testing OpenRouter Client")
    print("=" * 60)

    try:
        # Initialize client
        client = OpenRouterClient()
        print(f"✓ Client initialized successfully")
        print(f"  Model: {client.model}")
        print(f"  Temperature: {client.temperature}")
        print(f"  Max Tokens: {client.max_tokens}")

        # Test simple text generation
        prompt = "who are you?"
        print(f"\n📝 Testing text generation...")
        print(f"   Prompt: {prompt}")

        response = client.generate_text(prompt, max_tokens=100)

        print(f"\n✓ Response received:")
        print(f"   Length: {len(response)} characters")
        print(f"   Content: {response}")

        print("\n" + "=" * 60)
        print("✓ OpenRouter Client test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


    # from openai import OpenAI

    # client = OpenAI(
    # base_url="https://openrouter.ai/api/v1",
    # api_key="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",
    # )

    # completion = client.chat.completions.create(
    # #   extra_headers={
    # #     "HTTP-Referer": "<YOUR_SITE_URL>", # Optional. Site URL for rankings on openrouter.ai.
    # #     "X-Title": "<YOUR_SITE_NAME>", # Optional. Site title for rankings on openrouter.ai.
    # #   },
    # extra_body={},
    # temperature=0.4,
    # max_tokens=4000,
    # model="deepseek/deepseek-r1-distill-llama-70b:free",
    # messages=[
    #     {
    #     "role": "system",
    #     "content": "You are a helpful assistant that provides accurate and factual information."
    #     },
    #     {
    #     "role": "user",
    #     "content": "What is the meaning of life?"
    #     }
    # ]
    # )
    # print(completion.choices[0].message.content)