"""
Fallback-specific configuration for Portkey AI Gateway demos.

This module provides configuration helpers specifically for demonstrating
Portkey's fallback capabilities.
"""

import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OLLAMA_CONFIG, LLAMA_FP8_CONFIG

# =============================================================================
# Fallback Test Configurations
# =============================================================================

# Invalid endpoint (for fallback testing)
INVALID_OLLAMA_CONFIG = {
    "provider": "ollama",
    "custom_host": "http://invalid-endpoint:9999",
    "model": "llama3",
}

# =============================================================================
# Portkey Fallback Config Helpers
# =============================================================================

def create_fallback_config(
    primary_config: dict,
    fallback_config: dict,
    on_status_codes: list[int] = None
) -> dict:
    """
    Create a Portkey fallback configuration.

    Args:
        primary_config: Primary provider config (from OLLAMA_CONFIG or LLAMA_FP8_CONFIG)
        fallback_config: Fallback provider config
        on_status_codes: Optional list of HTTP status codes to trigger fallback

    Returns:
        Portkey config dictionary with fallback strategy
    """
    config = {
        "strategy": {
            "mode": "fallback"
        },
        "targets": [
            {
                "provider": primary_config["provider"],
                "api_key": "dummy-key-not-needed",
                "custom_host": primary_config["custom_host"],
                "override_params": {
                    "model": primary_config["model"]
                }
            },
            {
                "provider": fallback_config["provider"],
                "api_key": "dummy-key-not-needed",
                "custom_host": fallback_config["custom_host"],
                "override_params": {
                    "model": fallback_config["model"]
                }
            }
        ]
    }

    if on_status_codes:
        config["strategy"]["on_status_codes"] = on_status_codes

    return config


def create_invalid_provider_config(base_config: dict) -> dict:
    """
    Create an invalid provider config for testing fallback.

    Args:
        base_config: Base config to clone

    Returns:
        Config with invalid endpoint
    """
    invalid_config = base_config.copy()
    invalid_config["custom_host"] = "http://invalid-endpoint:9999"
    return invalid_config
