#!/usr/bin/env python3
"""
AI Configuration Loader
Loads and manages AI processing configuration from ai_config.yaml
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class AIConfig:
    """Manages AI configuration from YAML file."""

    def __init__(self, config_path: str = None):
        # Default to ../config/ai_config.yaml relative to this file
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "ai_config.yaml"
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Load custom personas if available
        self.custom_personas_path = Path(__file__).parent.parent / "config" / "custom_personas.yaml"
        self.custom_personas = self._load_custom_personas()

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"AI configuration file not found: {self.config_path}\n"
                f"Please ensure ai_config.yaml exists in the application directory."
            )

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_custom_personas(self) -> dict:
        """Load custom personas from custom_personas.yaml if it exists."""
        if not self.custom_personas_path.exists():
            return {}

        try:
            with open(self.custom_personas_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('personas', {}) if data else {}
        except Exception as e:
            print(f"Warning: Could not load custom personas: {e}")
            return {}

    def get_api_key(self) -> Optional[str]:
        """Get OpenRouter API key from environment variable."""
        env_var = self.config['openrouter']['api_key_env']
        api_key = os.getenv(env_var)

        if not api_key:
            return None

        return api_key

    def get_base_url(self) -> str:
        """Get OpenRouter base URL."""
        return self.config['openrouter']['base_url']

    def get_timeout(self) -> float:
        """Get API timeout in seconds."""
        return self.config['openrouter'].get('timeout', 10.0)

    def get_models(self) -> List[Dict]:
        """Get list of available models."""
        return self.config['openrouter']['models']

    def get_model_by_id(self, model_id: str) -> Optional[Dict]:
        """Get model configuration by ID."""
        for model in self.get_models():
            if model['id'] == model_id:
                return model
        return None

    def get_default_model(self) -> str:
        """Get default model ID."""
        return self.config['defaults']['model']

    def get_prompt(self, mode: str) -> str:
        """
        Get system prompt for the specified mode.

        Args:
            mode: 'translate' or 'proofread_translate'

        Returns:
            System prompt template string
        """
        if mode not in self.config['prompts']:
            raise ValueError(f"Unknown mode: {mode}. Use 'translate' or 'proofread_translate'")

        return self.config['prompts'][mode]['system']

    def get_defaults(self) -> Dict:
        """Get default settings."""
        return self.config['defaults']

    def get_personas(self) -> List[Dict]:
        """
        Get list of all available personas (built-in + custom).

        Returns:
            List of persona dictionaries with id, name, description
        """
        personas = []

        # Add built-in personas
        personas.append({
            'id': 'proofread',
            'name': 'Proofread',
            'description': 'Fix spelling and grammar errors only',
            'builtin': True
        })

        # Add custom personas
        for persona_id, persona_data in self.custom_personas.items():
            personas.append({
                'id': persona_id,
                'name': persona_data.get('name', persona_id),
                'description': persona_data.get('description', ''),
                'builtin': False
            })

        return personas

    def get_persona_prompt(self, persona_id: str) -> Optional[str]:
        """
        Get system prompt for a specific persona.

        Args:
            persona_id: ID of the persona ('proofread' or custom persona ID)

        Returns:
            System prompt string or None if not found
        """
        # Check built-in personas
        if persona_id in self.config['prompts']:
            return self.config['prompts'][persona_id]['system']

        # Check custom personas
        if persona_id in self.custom_personas:
            return self.custom_personas[persona_id].get('system_prompt')

        return None

    def format_prompt(self, mode: str, source_lang: str = None, target_lang: str = None) -> str:
        """
        Get formatted system prompt with language substitution.

        Args:
            mode: 'proofread', 'translate', or 'proofread_translate'
            source_lang: Source language code or 'auto' (optional for proofread mode)
            target_lang: Target language code (optional for proofread mode)

        Returns:
            Formatted system prompt
        """
        template = self.get_prompt(mode)

        # Proofread mode doesn't need language substitution
        if mode == 'proofread':
            return template

        # Format source language
        if source_lang == 'auto' or not source_lang:
            source_display = "the source language"
        else:
            source_display = source_lang

        return template.format(
            source_lang=source_display,
            target_lang=target_lang
        )

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return self.get_api_key() is not None

    def get_config_status(self) -> Dict:
        """
        Get configuration status for debugging.

        Returns:
            Dictionary with configuration status
        """
        api_key = self.get_api_key()

        return {
            'config_file_exists': self.config_path.exists(),
            'api_key_configured': api_key is not None,
            'api_key_env_var': self.config['openrouter']['api_key_env'],
            'num_models': len(self.get_models()),
            'default_model': self.get_default_model()
        }


# Convenience function for quick access
def load_ai_config() -> Optional[AIConfig]:
    """
    Load AI configuration, returning None if not available.

    Returns:
        AIConfig instance or None if configuration unavailable
    """
    try:
        config = AIConfig()
        if not config.is_configured():
            print("Warning: OPENROUTER_API_KEY environment variable not set")
            return None
        return config
    except FileNotFoundError as e:
        print(f"Warning: {e}")
        return None
    except Exception as e:
        print(f"Error loading AI configuration: {e}")
        return None


if __name__ == "__main__":
    """Test configuration loading."""
    print("Testing AI Configuration...\n")

    try:
        config = AIConfig()
        status = config.get_config_status()

        print("Configuration Status:")
        print(f"  Config file: {'✓' if status['config_file_exists'] else '✗'}")
        print(f"  API key: {'✓' if status['api_key_configured'] else '✗'} (env: {status['api_key_env_var']})")
        print(f"  Models available: {status['num_models']}")
        print(f"  Default model: {status['default_model']}")

        if status['api_key_configured']:
            print("\n✓ Configuration is ready!")
        else:
            print(f"\n✗ Please set {status['api_key_env_var']} environment variable")
            print("  Example: export OPENROUTER_API_KEY='your-key-here'")

        print("\nAvailable models:")
        for model in config.get_models():
            print(f"  - {model['name']}: {model['description']}")

    except Exception as e:
        print(f"✗ Error: {e}")
