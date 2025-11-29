#!/usr/bin/env python3
"""
OpenRouter AI Provider
Handles text processing via OpenRouter API
"""

import time
import requests
from typing import Optional, Tuple
from ai_config import AIConfig


class OpenRouterProvider:
    """
    OpenRouter API provider for AI text processing.
    Supports proofreading and translation via various AI models.
    """

    def __init__(self, config: AIConfig, model_id: Optional[str] = None):
        """
        Initialize OpenRouter provider.

        Args:
            config: AIConfig instance
            model_id: Model ID to use (defaults to config default)
        """
        self.config = config
        self.api_key = config.get_api_key()
        self.base_url = config.get_base_url()
        self.timeout = config.get_timeout()
        self.model_id = model_id or config.get_default_model()

        if not self.api_key:
            raise ValueError(
                f"OpenRouter API key not found. "
                f"Please set {config.config['openrouter']['api_key_env']} environment variable."
            )

        # Get model configuration
        self.model_config = config.get_model_by_id(self.model_id)
        if not self.model_config:
            raise ValueError(f"Model not found in configuration: {self.model_id}")

    def process_text(
        self,
        text: str,
        system_prompt: str,
        temperature: float = 0.3,
        max_retries: int = 2
    ) -> Tuple[str, Optional[str]]:
        """
        Process text using OpenRouter API.

        Args:
            text: Text to process
            system_prompt: System prompt for the AI
            temperature: Sampling temperature (0.0-1.0)
            max_retries: Number of retry attempts on failure

        Returns:
            Tuple of (processed_text, error_message)
            - If successful: (processed_text, None)
            - If failed: (original_text, error_message)
        """
        if not text or not text.strip():
            return ("", None)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/anthropics/whispering",
            "X-Title": "Whispering AI Text Processor"
        }

        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": temperature,
            "max_tokens": self.model_config.get('max_tokens', 4096)
        }

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )

                # Check for HTTP errors
                if response.status_code != 200:
                    error_detail = response.text[:200]
                    last_error = f"HTTP {response.status_code}: {error_detail}"

                    # Don't retry on authentication errors
                    if response.status_code in (401, 403):
                        return (text, f"Authentication error: {last_error}")

                    # Retry on server errors
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        return (text, last_error)

                # Parse response
                result = response.json()

                if 'choices' not in result or len(result['choices']) == 0:
                    last_error = "Invalid API response: no choices returned"
                    if attempt < max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        return (text, last_error)

                processed_text = result['choices'][0]['message']['content'].strip()
                return (processed_text, None)

            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue

            except requests.exceptions.ConnectionError:
                last_error = "Connection error"
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue

        # All retries failed
        return (text, f"Failed after {max_retries + 1} attempts: {last_error}")

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test API connection with a simple request.

        Returns:
            Tuple of (success, message)
        """
        try:
            test_text = "Hello"
            test_prompt = "Respond with just the word 'OK'"

            result, error = self.process_text(
                text=test_text,
                system_prompt=test_prompt,
                max_retries=1
            )

            if error:
                return (False, f"Connection test failed: {error}")

            return (True, f"Connection successful (model: {self.model_config['name']})")

        except Exception as e:
            return (False, f"Connection test error: {str(e)}")


class AITextProcessor:
    """
    High-level text processor for proofreading and translation.
    """

    def __init__(
        self,
        config: AIConfig,
        model_id: Optional[str] = None,
        mode: str = "proofread_translate",
        source_lang: Optional[str] = None,
        target_lang: Optional[str] = None
    ):
        """
        Initialize AI text processor.

        Args:
            config: AIConfig instance
            model_id: Model to use (defaults to config default)
            mode: 'translate' or 'proofread_translate'
            source_lang: Source language (None or 'auto' for auto-detect)
            target_lang: Target language code
        """
        self.config = config
        self.provider = OpenRouterProvider(config, model_id)
        self.mode = mode
        self.source_lang = source_lang
        self.target_lang = target_lang

        # Validate mode
        if mode not in ['translate', 'proofread_translate']:
            raise ValueError(f"Invalid mode: {mode}. Use 'translate' or 'proofread_translate'")

        # Get system prompt
        self.system_prompt = config.format_prompt(mode, source_lang or 'auto', target_lang)

        # Get defaults
        defaults = config.get_defaults()
        self.temperature = defaults.get('temperature', 0.3)
        self.max_retries = defaults.get('max_retries', 2)

    def process(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Process text (proofread and/or translate).

        Args:
            text: Text to process

        Returns:
            Tuple of (processed_text, error_message)
        """
        return self.provider.process_text(
            text=text,
            system_prompt=self.system_prompt,
            temperature=self.temperature,
            max_retries=self.max_retries
        )


if __name__ == "__main__":
    """Test the provider."""
    import sys

    print("Testing OpenRouter Provider...\n")

    try:
        config = AIConfig()

        if not config.is_configured():
            print("✗ API key not configured")
            print(f"  Please set {config.config['openrouter']['api_key_env']} environment variable")
            sys.exit(1)

        print(f"Using model: {config.get_default_model()}")

        # Test connection
        provider = OpenRouterProvider(config)
        success, message = provider.test_connection()

        if success:
            print(f"✓ {message}\n")

            # Test translation
            print("Testing translation mode...")
            processor = AITextProcessor(
                config=config,
                mode="translate",
                source_lang="en",
                target_lang="es"
            )

            test_text = "Hello, how are you today?"
            result, error = processor.process(test_text)

            if error:
                print(f"✗ Translation failed: {error}")
            else:
                print(f"  Input: {test_text}")
                print(f"  Output: {result}")
                print("✓ Translation test passed\n")

            # Test proofread + translate
            print("Testing proofread + translate mode...")
            processor2 = AITextProcessor(
                config=config,
                mode="proofread_translate",
                source_lang="en",
                target_lang="fr"
            )

            test_text2 = "Ths is a tets with speling erors."
            result2, error2 = processor2.process(test_text2)

            if error2:
                print(f"✗ Proofread+translate failed: {error2}")
            else:
                print(f"  Input: {test_text2}")
                print(f"  Output: {result2}")
                print("✓ Proofread+translate test passed")

        else:
            print(f"✗ {message}")
            sys.exit(1)

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
