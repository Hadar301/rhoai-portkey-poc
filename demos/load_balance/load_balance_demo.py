#!/usr/bin/env python3
"""
Portkey AI Gateway - Load Balancing Demo

This demo demonstrates Portkey's load balancing capabilities by:
1. Distributing requests across multiple LLM providers
2. Comparing round-robin vs weighted load balancing
3. Measuring distribution and performance metrics
4. Testing failover behavior when combined with load balancing

Usage:
    python load_balance_demo.py [--scenario round-robin|weighted|distribution|all]
"""

import argparse
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from portkey_ai import Portkey

import config as base_config
from load_balance.config import (
    create_round_robin_config,
    create_weighted_config,
)

# Import constants from base config
GATEWAY_API_URL = base_config.GATEWAY_API_URL
OLLAMA_CONFIG = base_config.OLLAMA_CONFIG
LLAMA_FP8_CONFIG = base_config.LLAMA_FP8_CONFIG
print_config = base_config.print_config


class LoadBalanceMetrics:
    """Track metrics for load balanced requests."""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency = 0.0
        self.latencies = []
        self.provider_distribution = Counter()

    def record_success(self, latency: float, provider: str = "unknown"):
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency += latency
        self.latencies.append(latency)
        self.provider_distribution[provider] += 1

    def record_failure(self, latency: float):
        self.total_requests += 1
        self.failed_requests += 1
        self.total_latency += latency

    def get_summary(self) -> dict:
        avg_latency = self.total_latency / self.total_requests if self.total_requests > 0 else 0
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0

        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": success_rate,
            "avg_latency": avg_latency,
            "min_latency": min(self.latencies) if self.latencies else 0,
            "max_latency": max(self.latencies) if self.latencies else 0,
            "distribution": dict(self.provider_distribution)
        }


def make_request_with_loadbalance(
    config: dict,
    message: str,
    max_tokens: int = 100
) -> Tuple[Optional[str], float, bool, Optional[str], Optional[str]]:
    """
    Make a chat completion request with load balancing configuration.

    Args:
        config: Portkey load balance config
        message: User message
        max_tokens: Maximum tokens in response

    Returns:
        Tuple of (response_content, latency, success, error_message, provider_used)
    """
    client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="not-needed-for-self-hosted",
        config=config
    )

    messages = [{"role": "user", "content": message}]

    start_time = time.time()
    try:
        # Note: Model is specified per provider in config, use generic model name here
        response = client.chat.completions.create(
            model="llama3",  # This will be interpreted by each provider
            messages=messages,
            max_tokens=max_tokens
        )
        latency = time.time() - start_time
        content = response.choices[0].message.content.strip()

        # Try to detect which provider was used based on response headers or metadata
        # Note: This might not be available in all Portkey versions
        provider_used = "unknown"
        if hasattr(response, '_headers'):
            provider_used = response._headers.get('x-portkey-provider', 'unknown')

        return content, latency, True, None, provider_used
    except Exception as e:
        latency = time.time() - start_time
        return None, latency, False, str(e), None


def test_round_robin_loadbalance() -> dict:
    """
    TEST 1: Round-Robin Load Balancing
    Distributes requests evenly across all providers.
    """
    print("\n" + "=" * 70)
    print("TEST 1: Round-Robin Load Balancing")
    print("=" * 70)

    # Create config with two different providers for load balancing
    targets = [OLLAMA_CONFIG, LLAMA_FP8_CONFIG]
    config = create_round_robin_config(targets)

    print("\nConfiguration:")
    print("  Strategy: Round-Robin (Equal Weights)")
    print("  Targets:")
    print(f"    1. {OLLAMA_CONFIG['provider']} - {OLLAMA_CONFIG['custom_host']}")
    print(f"    2. {LLAMA_FP8_CONFIG['provider']} - {LLAMA_FP8_CONFIG['custom_host']}")

    num_requests = 6
    test_messages = [
        "What is AI?",
        "What is Python?",
        "What is Docker?",
        "What is REST?",
        "What is CI/CD?",
        "What is Kubernetes?"
    ]

    print(f"\n[Testing] Sending {num_requests} requests with round-robin load balancing...")

    metrics = LoadBalanceMetrics()

    for i, msg in enumerate(test_messages[:num_requests]):
        print(f"\n[Request {i+1}/{num_requests}] '{msg[:40]}...'")

        content, latency, success, error, provider = make_request_with_loadbalance(
            config=config,
            message=msg
        )

        if success:
            metrics.record_success(latency, provider or "unknown")
            print(f"  SUCCESS: {content[:60]}...")
            print(f"  Latency: {latency:.3f}s | Provider: {provider or 'unknown'}")
        else:
            metrics.record_failure(latency)
            print(f"  FAILED: {error[:100]}")
            print(f"  Latency: {latency:.3f}s")

    # Print statistics
    summary = metrics.get_summary()
    print("\n  Statistics:")
    print(f"  - Total requests: {summary['total_requests']}")
    print(f"  - Successful: {summary['successful']}")
    print(f"  - Failed: {summary['failed']}")
    print(f"  - Success rate: {summary['success_rate']:.1f}%")
    print(f"  - Avg latency: {summary['avg_latency']:.3f}s")
    print(f"  - Min/Max latency: {summary['min_latency']:.3f}s / {summary['max_latency']:.3f}s")
    print("\n  Provider Distribution:")
    for provider, count in summary['distribution'].items():
        percentage = (count / summary['total_requests'] * 100) if summary['total_requests'] > 0 else 0
        print(f"    - {provider}: {count} requests ({percentage:.1f}%)")

    return {
        "test": "Round-Robin Load Balancing",
        **summary
    }


def test_weighted_loadbalance() -> dict:
    """
    TEST 2: Weighted Load Balancing
    Distributes requests based on configured weights.
    """
    print("\n" + "=" * 70)
    print("TEST 2: Weighted Load Balancing")
    print("=" * 70)

    # Create config with weighted distribution (70% Ollama, 30% LLaMA FP8)
    targets = [OLLAMA_CONFIG, LLAMA_FP8_CONFIG]
    weights = [0.25, 0.75]  # 70% vs 30%
    config = create_weighted_config(targets, weights)

    print("\nConfiguration:")
    print("  Strategy: Weighted Load Balancing")
    print("  Targets:")
    for i, (target, weight) in enumerate(zip(targets, weights)):
        percentage = weight * 100
        print(f"    {i+1}. {target['provider']} - Weight: {weight} ({percentage:.0f}%)")

    num_requests = 10
    test_messages = [
        f"Question {i+1}: What is the meaning of life?"
        for i in range(num_requests)
    ]

    print(f"\n[Testing] Sending {num_requests} requests with weighted load balancing...")

    metrics = LoadBalanceMetrics()

    for i, msg in enumerate(test_messages[:num_requests]):
        print(f"\n[Request {i+1}/{num_requests}]")

        content, latency, success, error, provider = make_request_with_loadbalance(
            config=config,
            message=msg
        )

        if success:
            metrics.record_success(latency, provider or "unknown")
            print(f"  SUCCESS: Latency: {latency:.3f}s | Provider: {provider or 'unknown'}")
        else:
            metrics.record_failure(latency)
            print(f"  FAILED: {error[:100]} | Latency: {latency:.3f}s")

    # Print statistics
    summary = metrics.get_summary()
    print("\n  Statistics:")
    print(f"  - Total requests: {summary['total_requests']}")
    print(f"  - Successful: {summary['successful']}")
    print(f"  - Failed: {summary['failed']}")
    print(f"  - Success rate: {summary['success_rate']:.1f}%")
    print(f"  - Avg latency: {summary['avg_latency']:.3f}s")
    print("\n  Provider Distribution:")
    for provider, count in summary['distribution'].items():
        actual_pct = (count / summary['total_requests'] * 100) if summary['total_requests'] > 0 else 0
        print(f"    - {provider}: {count} requests ({actual_pct:.1f}%)")

    # Compare with expected distribution
    expected_dist = {
        targets[0]['provider']: weights[0] / sum(weights) * 100,
        targets[1]['provider']: weights[1] / sum(weights) * 100
    }
    print("\n  Expected Distribution:")
    for provider, pct in expected_dist.items():
        print(f"    - {provider}: {pct:.0f}%")

    return {
        "test": "Weighted Load Balancing",
        **summary
    }


def test_distribution_analysis() -> dict:
    """
    TEST 3: Distribution Analysis
    Sends many requests to verify load distribution.
    """
    print("\n" + "=" * 70)
    print("TEST 3: Load Distribution Analysis (20 Requests)")
    print("=" * 70)

    targets = [OLLAMA_CONFIG, LLAMA_FP8_CONFIG]
    config = create_round_robin_config(targets)

    print("\nConfiguration:")
    print("  Strategy: Round-Robin")
    print("  Targets: 2 providers (Ollama & LLaMA FP8)")
    print("  Expected Distribution: 50% / 50%")

    num_requests = 20
    print(f"\n[Testing] Sending {num_requests} quick requests...")

    metrics = LoadBalanceMetrics()

    for i in range(num_requests):
        if (i + 1) % 5 == 0:
            print(f"  Progress: {i+1}/{num_requests} requests sent...")

        content, latency, success, error, provider = make_request_with_loadbalance(
            config=config,
            message=f"Count to {i+1}",
            max_tokens=50
        )

        if success:
            metrics.record_success(latency, provider or "unknown")
        else:
            metrics.record_failure(latency)

    # Print statistics
    summary = metrics.get_summary()
    print("\n  Results:")
    print(f"  - Total requests: {summary['total_requests']}")
    print(f"  - Successful: {summary['successful']} ({summary['success_rate']:.1f}%)")
    print(f"  - Avg latency: {summary['avg_latency']:.3f}s")

    print("\n  Distribution Analysis:")
    for provider, count in summary['distribution'].items():
        actual_pct = (count / summary['total_requests'] * 100) if summary['total_requests'] > 0 else 0
        expected_pct = 50.0  # For round-robin with 2 providers
        deviation = abs(actual_pct - expected_pct)
        print(f"    - {provider}: {count} requests ({actual_pct:.1f}%)")
        print(f"      Expected: {expected_pct:.0f}% | Deviation: {deviation:.1f}%")

    return {
        "test": "Distribution Analysis",
        **summary
    }


def print_results_table(results: list[dict]):
    """Print formatted results summary."""
    print("\n" + "=" * 70)
    print("LOAD BALANCING DEMO RESULTS SUMMARY")
    print("=" * 70)

    for r in results:
        print(f"\n{r['test']}:")
        print(f"  - Total Requests: {r['total_requests']}")
        print(f"  - Success Rate: {r['success_rate']:.1f}%")
        print(f"  - Avg Latency: {r['avg_latency']:.3f}s")
        if 'distribution' in r:
            print(f"  - Distribution: {r['distribution']}")


def main():
    parser = argparse.ArgumentParser(
        description="Portkey AI Gateway - Load Balancing Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run all tests (default)
    python load_balance_demo.py

    # Run specific scenario
    python load_balance_demo.py --scenario round-robin
    python load_balance_demo.py --scenario weighted
    python load_balance_demo.py --scenario distribution
        """
    )
    parser.add_argument(
        "--scenario",
        choices=["round-robin", "weighted", "distribution", "all"],
        default="all",
        help="Which load balancing scenario to test (default: all)"
    )

    args = parser.parse_args()

    # Print configuration
    print_config()

    results = []

    try:
        if args.scenario in ["round-robin", "all"]:
            results.append(test_round_robin_loadbalance())

        if args.scenario in ["weighted", "all"]:
            results.append(test_weighted_loadbalance())

        if args.scenario in ["distribution", "all"]:
            results.append(test_distribution_analysis())

        # Print summary
        print_results_table(results)

        print("\n✓ Demo completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
