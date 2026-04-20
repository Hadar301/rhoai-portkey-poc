"""
Load balancing-specific configuration for Portkey AI Gateway demos.

This module provides configuration helpers specifically for demonstrating
Portkey's load balancing capabilities across different LLM providers.
"""

import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import OLLAMA_CONFIG, LLAMA_FP8_CONFIG

# =============================================================================
# Portkey Load Balance Config Helpers
# =============================================================================

def create_loadbalance_config(
    targets: list[dict],
    weights: list[float] = None
) -> dict:
    """
    Create a Portkey load balancing configuration.

    Args:
        targets: List of provider configs (from OLLAMA_CONFIG, LLAMA_FP8_CONFIG, etc.)
        weights: Optional list of weights for weighted load balancing.
                Weights should be decimals that sum to 1.0 (e.g., [0.7, 0.3]).
                If None, uses round-robin (equal weights).

    Returns:
        Portkey config dictionary with load balancing strategy
    """
    if weights is None:
        # Equal weights for round-robin
        weight_value = 1.0 / len(targets)
        weights = [weight_value] * len(targets)

    if len(targets) != len(weights):
        raise ValueError("Number of targets must match number of weights")

    # Normalize weights to sum to 1.0
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    config = {
        "strategy": {
            "mode": "loadbalance"
        },
        "targets": []
    }

    for target, weight in zip(targets, normalized_weights):
        target_config = {
            "provider": target["provider"],
            "api_key": "dummy-key-not-needed",
            "custom_host": target["custom_host"],
            "weight": weight,
            "override_params": {
                "model": target["model"]
            }
        }
        config["targets"].append(target_config)

    return config


def create_round_robin_config(targets: list[dict]) -> dict:
    """
    Create a round-robin load balancing config (equal weights).

    Args:
        targets: List of provider configs

    Returns:
        Portkey config with round-robin load balancing
    """
    return create_loadbalance_config(targets, weights=None)


def create_weighted_config(targets: list[dict], weights: list[float]) -> dict:
    """
    Create a weighted load balancing config.

    Args:
        targets: List of provider configs
        weights: List of weights (e.g., [0.7, 0.3] for 70%-30% split).
                Will be automatically normalized to sum to 1.0.

    Returns:
        Portkey config with weighted load balancing
    """
    return create_loadbalance_config(targets, weights=weights)
