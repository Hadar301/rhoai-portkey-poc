"""
RHOAI KServe Connectivity Test

Validates that the Portkey gateway can reach RHOAI-deployed models
via their KServe InferenceService endpoints.

Usage:
    uv run python demos/rhoai/connectivity_test.py [--provider rhoai-primary|rhoai-secondary|all]
"""

import argparse
import sys
import time
from pathlib import Path

from portkey_ai import Portkey
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    GATEWAY_API_URL,
    OLLAMA_CONFIG,
    RHOAI_VLLM_PRIMARY_CONFIG,
    RHOAI_VLLM_SECONDARY_CONFIG,
    get_provider_config,
)


def test_provider_connectivity(
    gateway_url: str, provider_config: dict, provider_name: str
) -> dict:
    """
    Test connectivity to a single provider through the Portkey gateway.

    Returns:
        dict with keys: provider, status, latency_ms, model, error
    """
    result = {
        "provider": provider_name,
        "endpoint": provider_config["custom_host"],
        "model": provider_config["model"],
        "status": "UNKNOWN",
        "latency_ms": 0,
        "error": None,
    }

    try:
        client = Portkey(
            base_url=gateway_url,
            provider=provider_config["provider"],
            custom_host=provider_config["custom_host"],
            api_key="dummy-key",
        )

        start = time.time()
        response = client.chat.completions.create(
            model=provider_config["model"],
            messages=[{"role": "user", "content": "Say 'hello' in one word."}],
            max_tokens=10,
        )
        elapsed = (time.time() - start) * 1000

        result["status"] = "OK"
        result["latency_ms"] = round(elapsed, 1)

        if response.choices:
            content = response.choices[0].message.content
            result["response"] = content[:50] if content else "(empty)"

    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = str(e)[:80]

    return result


def main():
    parser = argparse.ArgumentParser(description="Test RHOAI model connectivity")
    parser.add_argument(
        "--provider",
        choices=["rhoai-primary", "rhoai-secondary", "ollama", "all"],
        default="all",
        help="Provider to test (default: all)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("RHOAI KServe Connectivity Test")
    print("=" * 70)
    print(f"Gateway URL: {GATEWAY_API_URL}")
    print()

    providers_to_test = []

    if args.provider == "all":
        providers_to_test = [
            ("rhoai-primary", RHOAI_VLLM_PRIMARY_CONFIG),
            ("rhoai-secondary", RHOAI_VLLM_SECONDARY_CONFIG),
            ("ollama", OLLAMA_CONFIG),
        ]
    else:
        config = get_provider_config(args.provider)
        providers_to_test = [(args.provider, config)]

    results = []
    for name, config in providers_to_test:
        print(f"Testing {name}...", end=" ", flush=True)
        result = test_provider_connectivity(GATEWAY_API_URL, config, name)
        status_icon = "OK" if result["status"] == "OK" else "FAIL"
        print(f"[{status_icon}]")
        results.append(result)

    print()
    print("=" * 70)
    print("Results")
    print("=" * 70)

    table_data = []
    for r in results:
        table_data.append(
            [
                r["provider"],
                r["model"],
                r["status"],
                f"{r['latency_ms']}ms" if r["latency_ms"] else "-",
                r.get("error", r.get("response", "-")) or "-",
            ]
        )

    print(
        tabulate(
            table_data,
            headers=["Provider", "Model", "Status", "Latency", "Details"],
            tablefmt="grid",
        )
    )

    # Summary
    passed = sum(1 for r in results if r["status"] == "OK")
    total = len(results)
    print()
    print(f"Connectivity: {passed}/{total} providers reachable")

    if passed < total:
        print()
        print("Failed providers:")
        for r in results:
            if r["status"] != "OK":
                print(f"  - {r['provider']}: {r['error']}")
        sys.exit(1)
    else:
        print("All providers are reachable.")


if __name__ == "__main__":
    main()
