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

# A truncated response shorter than this is a stub (a bare title, a half
# sentence) rather than a usable report, so it is retried instead of returned.
MIN_USABLE_RESPONSE_CHARS = 200


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
        
        # Initialize OpenAI client with OpenRouter base URL
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

        # Get settings from config
        self.model = config.get("model", "deepseek/deepseek-r1-distill-llama-70b:free")
        self.temperature = config.get("temperature", 0.4)
        self.max_tokens = config.get("max_tokens", 4000)
        self.reasoning_enabled = config.get("reasoning_enabled", False)

        logger.info(
            f"OpenRouter API client initialized with model: {self.model} "
            f"(reasoning={'on' if self.reasoning_enabled else 'off'})"
        )

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
            extra_body={"reasoning": {"enabled": self.reasoning_enabled}}
        )

        # Extract the generated text
        choice = response.choices[0]
        generated_text = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None)

        # Clean the response using base class method
        generated_text = self._clean_response(generated_text) if generated_text else ""

        # finish_reason == "length" means the model ran out of budget mid-answer.
        # With a reasoning model this happens even at large max_tokens, because
        # chain-of-thought is billed first and can leave nothing for `content`.
        if finish_reason == "length":
            logger.warning(
                f"Response truncated by max_tokens={tokens}: got {len(generated_text)} chars"
                f"{self._reasoning_token_hint(response)}"
            )
            if len(generated_text) < MIN_USABLE_RESPONSE_CHARS:
                # Unusable - report as empty so @retry_on_empty_response retries
                # instead of shipping a stub report.
                logger.error("Truncated response too short to use, treating as empty")
                return ""

        logger.info(f"Successfully generated text ({len(generated_text)} chars)")
        return generated_text

    @staticmethod
    def _reasoning_token_hint(response) -> str:
        """Report reasoning token spend, to make budget starvation obvious in logs."""
        usage = getattr(response, "usage", None)
        details = getattr(usage, "completion_tokens_details", None) if usage else None
        reasoning_tokens = getattr(details, "reasoning_tokens", None) if details else None
        if not reasoning_tokens:
            return ""
        return (f" ({reasoning_tokens} tokens went to reasoning - set "
                f"OPENROUTER_REASONING_ENABLED=false or raise LLM_MAX_TOKENS)")


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

        response = client.generate_text(prompt, max_tokens=500)

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
