"""
Groq API Client

This module provides functionality to interact with the Groq API for LLM processing.
"""

import os
import sys
import logging
from typing import Optional
import groq
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from config import LLM_PROVIDERS
from services.llm_processing.clients.base_client import BaseLLMClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroqClient(BaseLLMClient):
    """Client for interacting with the Groq API."""

    def __init__(self):
        """Initialize the Groq API client using credentials from config."""
        super().__init__()

        # Get Groq config
        config = LLM_PROVIDERS.get("groq", {})

        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Groq API key not found in configuration")

        self.client = groq.Client(api_key=self.api_key)
        self.model = config.get("model", "llama-3.3-70b-versatile")
        self.temperature = config.get("temperature", 0.4)
        self.max_tokens = config.get("max_tokens", 4000)

        logger.info(f"Groq API client initialized with model: {self.model}")

    def generate_text(self,
                     prompt: str,
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None) -> str:
        """
        Generate text using the Groq API.

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

        try:
            # Call the Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides accurate and factual information."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temp,
                max_tokens=tokens
            )

            # Extract the generated text
            generated_text = response.choices[0].message.content

            # Clean the response using base class method
            generated_text = self._clean_response(generated_text)

            logger.info(f"Successfully generated text ({len(generated_text)} chars)")
            return generated_text

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise


if __name__ == "__main__":
    """Simple test for Groq client."""
    print("=" * 60)
    print("Testing Groq Client")
    print("=" * 60)

    try:
        # Initialize client
        client = GroqClient()
        print(f"✓ Client initialized successfully")
        print(f"  Model: {client.model}")
        print(f"  Temperature: {client.temperature}")
        print(f"  Max Tokens: {client.max_tokens}")

        # Test simple text generation
        prompt = "What is deep learning? Answer in one sentence."
        print(f"\n📝 Testing text generation...")
        print(f"   Prompt: {prompt}")

        response = client.generate_text(prompt, max_tokens=100)

        print(f"\n✓ Response received:")
        print(f"   Length: {len(response)} characters")
        print(f"   Content: {response}")

        print("\n" + "=" * 60)
        print("✓ Groq Client test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
