"""
Shared configuration for Portkey AI Gateway demos.

This module provides centralized configuration for connecting to the Portkey gateway
and LLM providers deployed on OpenShift.
"""

import os

# =============================================================================
# Gateway Configuration
# =============================================================================

# Portkey Gateway URL - set via environment variable or use default
# When running inside the cluster, use the service URL
# When running outside, use the route URL (get with: oc get route portkey-gateway -o jsonpath='{.spec.host}')
GATEWAY_URL = os.environ.get(
    "PORTKEY_GATEWAY_URL",
    "https://portkey-gateway-hacohen-portkey.apps.ai-dev02.kni.syseng.devcluster.openshift.com"
)

# For SDK usage, we need the base URL without /v1
GATEWAY_BASE_URL = GATEWAY_URL.rstrip("/")
if not GATEWAY_BASE_URL.endswith("/v1"):
    GATEWAY_API_URL = f"{GATEWAY_BASE_URL}/v1"
else:
    GATEWAY_API_URL = GATEWAY_BASE_URL

# =============================================================================
# Provider Configurations
# =============================================================================

# Ollama (local LLM via Portkey gateway)
OLLAMA_CONFIG = {
    "provider": "ollama",
    "custom_host": "http://portkey-gateway-ollama:11434",
    "model": "llama3",
}

# LLaMA FP8 (vLLM deployment)
LLAMA_FP8_CONFIG = {
    "provider": "openai",  # vLLM is OpenAI-compatible
    "custom_host": "http://llama-fp8-predictor.hacohen-llmlite:8080/v1",
    "model": "llama-fp8",
}

# Invalid endpoint (for fallback testing)
INVALID_OLLAMA_CONFIG = {
    "provider": "ollama",
    "custom_host": "http://invalid-endpoint:9999",
    "model": "llama3",
}

# =============================================================================
# Default Settings
# =============================================================================

# Default provider to use in demos
DEFAULT_PROVIDER = OLLAMA_CONFIG

# Cache settings
CACHE_MAX_AGE = 300  # seconds (5 minutes)

# =============================================================================
# Helper Functions
# =============================================================================

def get_provider_config(provider_name: str = "ollama") -> dict:
    """
    Get configuration for a specific provider.
    
    Args:
        provider_name: Either "ollama" or "llama-fp8"
        
    Returns:
        Provider configuration dictionary
    """
    providers = {
        "ollama": OLLAMA_CONFIG,
        "llama-fp8": LLAMA_FP8_CONFIG,
    }
    return providers.get(provider_name, OLLAMA_CONFIG)


def print_config():
    """Print current configuration for debugging."""
    print("=" * 60)
    print("Portkey Gateway Demo Configuration")
    print("=" * 60)
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Gateway API URL: {GATEWAY_API_URL}")
    print()
    print("Available Providers:")
    print(f"  - Ollama: {OLLAMA_CONFIG['custom_host']}")
    print(f"    Model: {OLLAMA_CONFIG['model']}")
    print(f"  - LLaMA FP8: {LLAMA_FP8_CONFIG['custom_host']}")
    print(f"    Model: {LLAMA_FP8_CONFIG['model']}")
    print("=" * 60)


if __name__ == "__main__":
    print_config()

