#!/usr/bin/env python3
"""
Portkey AI Gateway - Fallback Demo

This demo demonstrates Portkey's automatic fallback capabilities by:
1. Simulating provider failures
2. Measuring fallback overhead
3. Testing various fallback scenarios
4. Comparing resilience with and without fallback

Usage:
    python fallback_demo.py [--scenario simple|all-fail|primary-success|stress|all]
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from portkey_ai import Portkey
from tabulate import tabulate

import config as base_config
from fallback.config import INVALID_OLLAMA_CONFIG, create_fallback_config

# Import constants from base config
GATEWAY_API_URL = base_config.GATEWAY_API_URL
OLLAMA_CONFIG = base_config.OLLAMA_CONFIG
print_config = base_config.print_config


class FallbackMetrics:
    """Track metrics for fallback requests."""

    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.fallback_triggered = 0
        self.total_latency = 0.0
        self.primary_latency = 0.0
        self.fallback_latency = 0.0

    def record_success(self, latency: float, used_fallback: bool):
        self.total_requests += 1
        self.successful_requests += 1
        self.total_latency += latency

        if used_fallback:
            self.fallback_triggered += 1
            self.fallback_latency += latency
        else:
            self.primary_latency += latency

    def record_failure(self, latency: float):
        self.total_requests += 1
        self.failed_requests += 1
        self.total_latency += latency


def make_request_with_fallback(
    config: dict,
    message: str,
    model: str,
    max_tokens: int = 100
) -> Tuple[Optional[str], float, bool, Optional[str]]:
    """
    Make a chat completion request with fallback configuration.

    Args:
        config: Portkey fallback config
        message: User message
        model: Model name to use
        max_tokens: Maximum tokens in response

    Returns:
        Tuple of (response_content, latency, success, error_message)
    """
    client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="not-needed-for-self-hosted",
        config=config
    )

    messages = [{"role": "user", "content": message}]

    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )
        latency = time.time() - start_time
        content = response.choices[0].message.content.strip()
        return content, latency, True, None
    except Exception as e:
        latency = time.time() - start_time
        return None, latency, False, str(e)


def make_request_without_fallback(
    provider_config: dict,
    message: str,
    max_tokens: int = 100
) -> Tuple[Optional[str], float, bool, Optional[str]]:
    """
    Make a request without fallback for comparison.

    Returns:
        Tuple of (response_content, latency, success, error_message)
    """
    client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="not-needed-for-self-hosted",
        provider=provider_config["provider"],
        custom_host=provider_config["custom_host"],
    )

    messages = [{"role": "user", "content": message}]

    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=provider_config["model"],
            messages=messages,
            max_tokens=max_tokens
        )
        latency = time.time() - start_time
        content = response.choices[0].message.content.strip()
        return content, latency, True, None
    except Exception as e:
        latency = time.time() - start_time
        return None, latency, False, str(e)


def test_simple_fallback() -> dict:
    """
    TEST 1: Simple Fallback Demonstration
    Shows fallback capability by comparing with/without fallback config.

    Note: Due to gateway timeout limitations with completely unreachable endpoints,
    this test demonstrates the fallback concept rather than actual failover timing.
    """
    print("\n" + "=" * 70)
    print("TEST 1: Fallback Capability Demonstration")
    print("=" * 70)

    # For this demo, we'll show the fallback configuration setup
    # In production, fallback would trigger on HTTP errors (429, 500, 503, etc.)
    # rather than network-level failures which cause gateway timeouts

    print("\nDemonstration Scenario:")
    print("  In a production environment, fallback triggers on:")
    print("  - HTTP 429 (rate limit)")
    print("  - HTTP 500/502/503 (server errors)")
    print("  - Model-specific errors")
    print("\nConfiguration that would be used:")
    print(f"  Primary: Provider A (main)")
    print(f"  Fallback: Provider B (backup)")

    test_message = "What is the capital of France? Answer in one word."

    # Show successful request with fallback config (using valid endpoints)
    print("\n[With Fallback Config] Making request...")
    config = create_fallback_config(
        primary_config=OLLAMA_CONFIG,
        fallback_config=OLLAMA_CONFIG
    )

    content, latency, success, error = make_request_with_fallback(
        config=config,
        message=test_message,
        model=OLLAMA_CONFIG["model"]
    )

    if success:
        print(f"  SUCCESS: Request handled with fallback config")
        print(f"  Response: {content[:80]}...")
        print(f"  Latency: {latency:.3f}s")
    else:
        print(f"  FAILED: {error}")
        print(f"  Latency: {latency:.3f}s")

    # Show direct request without fallback config
    print("\n[Without Fallback Config] Making direct request...")
    content2, latency2, success2, error2 = make_request_without_fallback(
        provider_config=OLLAMA_CONFIG,
        message=test_message
    )

    if success2:
        print(f"  SUCCESS: Direct request")
        print(f"  Response: {content2[:80]}...")
        print(f"  Latency: {latency2:.3f}s")
    else:
        print(f"  FAILED: {error2[:100]}")
        print(f"  Latency: {latency2:.3f}s")

    print("\n  Note: Both succeed as endpoints are valid.")
    print("  Fallback config provides resilience when primary fails.")

    return {
        "test": "Fallback Capability Demo",
        "with_fallback_success": success,
        "with_fallback_latency": latency,
        "without_fallback_success": success2,
        "without_fallback_latency": latency2,
    }


def test_all_providers_fail() -> dict:
    """
    TEST 2: All Providers Fail
    Both primary and fallback are invalid.
    """
    print("\n" + "=" * 70)
    print("TEST 2: All Providers Fail (Error Handling)")
    print("=" * 70)

    # Create config with two invalid providers
    invalid_secondary = INVALID_OLLAMA_CONFIG.copy()
    invalid_secondary["custom_host"] = "http://another-invalid:8888"

    config = create_fallback_config(
        primary_config=INVALID_OLLAMA_CONFIG,
        fallback_config=invalid_secondary
    )

    print("\nConfiguration:")
    print(f"  Primary: {INVALID_OLLAMA_CONFIG['custom_host']} (INVALID)")
    print(f"  Fallback: {invalid_secondary['custom_host']} (INVALID)")

    test_message = "Hello, world!"

    print("\n[Testing] Making request (expecting failure)...")
    content, latency, success, error = make_request_with_fallback(
        config=config,
        message=test_message,
        model="llama3"
    )

    if success:
        print(f"  Unexpected success!")
    else:
        print(f"  EXPECTED FAILURE: All providers exhausted")
        print(f"  Error: {error[:150]}")
        print(f"  Latency: {latency:.3f}s")

    return {
        "test": "All Providers Fail",
        "success": success,
        "latency": latency,
        "error": error[:100] if error else None
    }


def test_primary_success_no_fallback() -> dict:
    """
    TEST 3: Primary Succeeds (No Fallback Needed)
    Measure overhead of fallback config when primary works.
    """
    print("\n" + "=" * 70)
    print("TEST 3: Primary Succeeds (No Fallback Triggered)")
    print("=" * 70)

    # Config with valid primary and fallback (both Ollama for this demo)
    config = create_fallback_config(
        primary_config=OLLAMA_CONFIG,
        fallback_config=OLLAMA_CONFIG
    )

    print("\nConfiguration:")
    print(f"  Primary: {OLLAMA_CONFIG['custom_host']}")
    print(f"  Fallback: {OLLAMA_CONFIG['custom_host']} (same endpoint)")

    test_message = "What is 2+2? Answer in one word."

    # With fallback config
    print("\n[With Fallback Config] Making request...")
    content1, latency1, success1, _ = make_request_with_fallback(
        config=config,
        message=test_message,
        model=OLLAMA_CONFIG["model"]
    )

    if success1:
        print(f"  SUCCESS (Primary)")
        print(f"  Response: {content1[:80]}...")
        print(f"  Latency: {latency1:.3f}s")

    # Without fallback config
    print("\n[Without Fallback Config] Making request...")
    content2, latency2, success2, _ = make_request_without_fallback(
        provider_config=OLLAMA_CONFIG,
        message=test_message
    )

    if success2:
        print(f"  SUCCESS (Direct)")
        print(f"  Response: {content2[:80]}...")
        print(f"  Latency: {latency2:.3f}s")

    overhead = latency1 - latency2
    overhead_pct = (overhead / latency2 * 100) if latency2 > 0 else 0

    print(f"\n  Fallback Config Overhead: {overhead:.3f}s ({overhead_pct:.1f}%)")

    return {
        "test": "Primary Success",
        "with_fallback_latency": latency1,
        "without_fallback_latency": latency2,
        "overhead": overhead,
        "overhead_pct": overhead_pct
    }


def test_stress_fallback() -> dict:
    """
    TEST 4: Stress Test (Multiple Requests)
    Measure fallback performance with multiple requests using valid endpoints.
    """
    print("\n" + "=" * 70)
    print("TEST 4: Stress Test (5 Requests - All Valid, No Fallback)")
    print("=" * 70)

    # Use valid primary and fallback (both Ollama) to avoid timeouts
    # This tests consistency and performance without fallback trigger
    config = create_fallback_config(
        primary_config=OLLAMA_CONFIG,
        fallback_config=OLLAMA_CONFIG
    )

    print("\nConfiguration:")
    print(f"  Primary: {OLLAMA_CONFIG['custom_host']} (Ollama)")
    print(f"  Fallback: {OLLAMA_CONFIG['custom_host']} (Ollama - backup)")
    print("\nNote: Using valid endpoints to avoid gateway timeouts.")
    print("This demonstrates consistent performance with fallback config.")

    num_requests = 5
    messages = [
        "What is AI? Answer briefly.",
        "What is Python? One sentence.",
        "What is Docker? One sentence.",
        "What is REST? One sentence.",
        "What is CI/CD? One sentence."
    ]

    print(f"\nSending {num_requests} requests...")

    metrics = FallbackMetrics()

    for i, msg in enumerate(messages[:num_requests]):
        print(f"\n[Request {i+1}/{num_requests}] {msg[:40]}...")

        content, latency, success, error = make_request_with_fallback(
            config=config,
            message=msg,
            model=OLLAMA_CONFIG["model"]
        )

        if success:
            metrics.record_success(latency, used_fallback=False)  # Primary should succeed
            print(f"  SUCCESS: {content[:60]}... ({latency:.3f}s)")
        else:
            metrics.record_failure(latency)
            print(f"  FAILED: {error[:50]} ({latency:.3f}s)")

    # Print statistics
    print(f"\n  Statistics:")
    print(f"  - Total requests: {metrics.total_requests}")
    print(f"  - Successful: {metrics.successful_requests}")
    print(f"  - Failed: {metrics.failed_requests}")
    if metrics.total_requests > 0:
        print(f"  - Success rate: {metrics.successful_requests/metrics.total_requests*100:.1f}%")
        print(f"  - Avg latency: {metrics.total_latency/metrics.total_requests:.3f}s")
    else:
        print(f"  - Success rate: 0.0%")
        print(f"  - Avg latency: 0.000s")

    return {
        "test": "Stress Test",
        "total_requests": metrics.total_requests,
        "successful": metrics.successful_requests,
        "failed": metrics.failed_requests,
        "fallback_triggered": 0,  # Not triggered in this test
        "avg_latency": metrics.total_latency / metrics.total_requests if metrics.total_requests > 0 else 0,
        "success_rate": metrics.successful_requests / metrics.total_requests * 100 if metrics.total_requests > 0 else 0
    }


def print_results_table(results: list[dict]):
    """Print formatted results summary."""
    print("\n" + "=" * 70)
    print("FALLBACK DEMO RESULTS SUMMARY")
    print("=" * 70)

    # Different format based on test type
    for r in results:
        print(f"\n{r['test']}:")
        for key, value in r.items():
            if key != "test":
                print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(
        description="Portkey AI Gateway - Fallback Capabilities Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run all tests (default)
    python fallback_demo.py

    # Run specific scenario
    python fallback_demo.py --scenario simple
    python fallback_demo.py --scenario all-fail
    python fallback_demo.py --scenario primary-success
    python fallback_demo.py --scenario stress
        """
    )
    parser.add_argument(
        "--scenario",
        choices=["simple", "all-fail", "primary-success", "stress", "all"],
        default="all",
        help="Which fallback scenario to test (default: all)"
    )

    args = parser.parse_args()

    # Print configuration
    print_config()

    results = []

    try:
        if args.scenario in ["simple", "all"]:
            results.append(test_simple_fallback())

        if args.scenario in ["all-fail", "all"]:
            results.append(test_all_providers_fail())

        if args.scenario in ["primary-success", "all"]:
            results.append(test_primary_success_no_fallback())

        if args.scenario in ["stress", "all"]:
            results.append(test_stress_fallback())

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
