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
    "https://portkey-gateway-route.apps.example.cluster.local",  # Dummy cluster URL
    # Original: "https://portkey-portkey-gateway-hacohen-portkey.apps.ai-dev01.kni.syseng.devcluster.openshift.com"
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
    "custom_host": os.environ.get("OLLAMA_SERVICE_HOST", "http://ollama-service:11434"),  # Dummy service name
    # Original: "http://portkey-portkey-gateway-ollama:11434"
    "model": "llama3",
}

# LLaMA 3.2 1B FP8 (vLLM deployment in same namespace)
# Note: Portkey gateway rejects FQDN (.svc.cluster.local) as "Invalid custom host".
# Use short service names instead.
LLAMA_FP8_CONFIG = {
    "provider": "openai",  # vLLM is OpenAI-compatible
    "custom_host": os.environ.get("VLLM_SERVICE_HOST", "http://vllm-service:8080/v1"),  # Dummy service name
    # Original: "http://portkey-portkey-gateway-vllm-metrics:8080/v1"
    "model": "RedHatAI/granite-3.3-8b-instruct",
}

# =============================================================================
# RHOAI KServe Model Configurations
# =============================================================================

# RHOAI models namespace (where InferenceServices are deployed)
RHOAI_MODELS_NAMESPACE = os.environ.get("RHOAI_MODELS_NAMESPACE", "rhoai-models")

# RHOAI vLLM Model - Primary (configure via env vars or edit defaults)
RHOAI_VLLM_PRIMARY_CONFIG = {
    "provider": "openai",  # KServe vLLM exposes OpenAI-compatible API
    "custom_host": os.environ.get(
        "RHOAI_VLLM_PRIMARY_HOST", "http://rhoai-primary-model:8080/v1"  # Dummy RHOAI service name
        # Original: "http://portkey-portkey-gateway-vllm-metrics:8080/v1"
    ),
    "model": os.environ.get("RHOAI_VLLM_PRIMARY_MODEL", "RedHatAI/granite-3.3-8b-instruct"),
}

# Secondary model (Ollama - for failover/load-balancing demos)
RHOAI_VLLM_SECONDARY_CONFIG = {
    "provider": "ollama",
    "custom_host": os.environ.get(
        "RHOAI_VLLM_SECONDARY_HOST", "http://rhoai-secondary-model:11434"  # Dummy RHOAI secondary service name
        # Original: "http://portkey-portkey-gateway-ollama:11434"
    ),
    "model": os.environ.get("RHOAI_VLLM_SECONDARY_MODEL", "llama3"),
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
        provider_name: One of "ollama", "llama-fp8", "rhoai-primary", "rhoai-secondary"

    Returns:
        Provider configuration dictionary
    """
    providers = {
        "ollama": OLLAMA_CONFIG,
        "llama-fp8": LLAMA_FP8_CONFIG,
        "rhoai-primary": RHOAI_VLLM_PRIMARY_CONFIG,
        "rhoai-secondary": RHOAI_VLLM_SECONDARY_CONFIG,
    }
    return providers.get(provider_name, OLLAMA_CONFIG)


def validate_configuration():
    """
    Validate the current configuration and warn about potential issues.

    Returns:
        List of validation warnings/errors
    """
    warnings = []

    # Check for dummy/example values that need to be replaced
    if "example.cluster.local" in GATEWAY_URL:
        warnings.append("⚠️  Gateway URL contains example domain - set PORTKEY_GATEWAY_URL environment variable")

    if "ollama-service" in OLLAMA_CONFIG["custom_host"]:
        warnings.append("ℹ️  Using generic Ollama service name - set OLLAMA_SERVICE_HOST if different")

    if "vllm-service" in LLAMA_FP8_CONFIG["custom_host"]:
        warnings.append("ℹ️  Using generic vLLM service name - set VLLM_SERVICE_HOST if different")

    if "rhoai-primary-model" in RHOAI_VLLM_PRIMARY_CONFIG["custom_host"]:
        warnings.append("ℹ️  Using generic RHOAI service names - set RHOAI_VLLM_PRIMARY_HOST if using RHOAI")

    # Check for localhost usage (might indicate development vs production confusion)
    for config_name, config in [
        ("Ollama", OLLAMA_CONFIG),
        ("LLaMA FP8", LLAMA_FP8_CONFIG),
        ("RHOAI Primary", RHOAI_VLLM_PRIMARY_CONFIG),
        ("RHOAI Secondary", RHOAI_VLLM_SECONDARY_CONFIG)
    ]:
        if "localhost" in config.get("custom_host", ""):
            warnings.append(f"⚠️  {config_name} uses localhost - ensure port-forwarding is active or use service names")

    return warnings


def print_config():
    """Print current configuration for debugging."""
    print("=" * 60)
    print("Portkey Gateway Demo Configuration")
    print("=" * 60)
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Gateway API URL: {GATEWAY_API_URL}")
    print("\nAvailable Providers:")
    print(f"  - Ollama: {OLLAMA_CONFIG['custom_host']}")
    print(f"    Model: {OLLAMA_CONFIG['model']}")
    print(f"  - LLaMA FP8: {LLAMA_FP8_CONFIG['custom_host']}")
    print(f"    Model: {LLAMA_FP8_CONFIG['model']}")
    print(f"  - RHOAI Primary: {RHOAI_VLLM_PRIMARY_CONFIG['custom_host']}")
    print(f"    Model: {RHOAI_VLLM_PRIMARY_CONFIG['model']}")
    print(f"  - RHOAI Secondary: {RHOAI_VLLM_SECONDARY_CONFIG['custom_host']}")
    print(f"    Model: {RHOAI_VLLM_SECONDARY_CONFIG['model']}")

    # Show validation warnings
    warnings = validate_configuration()
    if warnings:
        print("\nConfiguration Notices:")
        for warning in warnings:
            print(f"  {warning}")
        print("\nℹ️  See .env.example for configuration examples")
    else:
        print("\n✅ Configuration appears to be customized")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
