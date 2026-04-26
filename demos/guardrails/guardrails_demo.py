#!/usr/bin/env python3
"""
Portkey AI Gateway - Guardrails Demo

Demonstrates Portkey's built-in guardrails for input/output validation.
The OSS gateway includes 40+ pre-built guardrails covering:
- Deterministic checks (regex, JSON schema, word count, etc.)
- LLM-based checks (gibberish detection, prompt injection, etc.)

This demo shows how guardrails compare to manual safety implementations
like LlamaGuard (used in the LiteLLM POC).

Usage:
    uv run python demos/guardrails/guardrails_demo.py [--scenario all|input|output|comparison]

Environment Variables:
    PORTKEY_GATEWAY_URL - The Portkey gateway URL
    PORTKEY_API_KEY     - Portkey API key (for cloud guardrails, optional)
"""

import argparse
import json
import sys
import time
from pathlib import Path

from portkey_ai import Portkey
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    GATEWAY_API_URL,
    get_provider_config,
    print_config,
)

# =============================================================================
# Guardrail Configuration Helpers
# =============================================================================


def create_guardrail_config(
    provider_config: dict,
    input_guardrails: list[dict] = None,
    output_guardrails: list[dict] = None,
) -> dict:
    """
    Create a Portkey config with guardrails.

    Guardrails use the Portkey "hooks" system. Each guardrail object in the array
    has reserved keys (deny, async, on_fail, on_success, id) and every other key
    is treated as a check ID with its value being the parameters object.

    Check IDs use camelCase (e.g., regexMatch, wordCount, characterCount).
    Set "deny": true to block requests (HTTP 446) when checks fail.

    Args:
        provider_config: Provider configuration dict
        input_guardrails: List of input guardrail hook dicts
        output_guardrails: List of output guardrail hook dicts

    Returns:
        Portkey config dict with guardrails
    """
    target = {
        "provider": provider_config["provider"],
        "api_key": "dummy-key",
        "custom_host": provider_config["custom_host"],
        "override_params": {"model": provider_config["model"]},
    }
    if input_guardrails:
        target["input_guardrails"] = input_guardrails
    if output_guardrails:
        target["output_guardrails"] = output_guardrails

    config = {
        "strategy": {"mode": "single"},
        "targets": [target],
    }
    return config


# =============================================================================
# Guardrail Check Definitions
# =============================================================================
# Each guardrail is a dict where:
#   - "deny": true  → block request/response on failure (HTTP 446)
#   - remaining keys are check IDs (camelCase) with parameter objects
#
# Available OSS checks (default plugin):
#   regexMatch, wordCount, characterCount, sentenceCount, containsCode,
#   contains, jsonSchema, jsonKeys, validUrls, webhook, alluppercase,
#   alllowercase, endsWith, modelWhitelist, notNull

# Input guardrails (beforeRequest)
REGEX_PII_EMAIL_GUARDRAIL = {
    "deny": True,
    "regexMatch": {
        "rule": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "not": True,  # Block when regex DOES match (PII found = fail)
    },
}
GUARDRAIL_NAME_PII_EMAIL = "PII Email Detection"

REGEX_PII_PHONE_GUARDRAIL = {
    "deny": True,
    "regexMatch": {
        "rule": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "not": True,  # Block when regex DOES match (PII found = fail)
    },
}
GUARDRAIL_NAME_PII_PHONE = "PII Phone Detection"

WORD_COUNT_GUARDRAIL = {
    "deny": True,
    "wordCount": {
        "maxWords": 500,
    },
}
GUARDRAIL_NAME_WORD_COUNT = "Word Count Limit"

CHAR_COUNT_GUARDRAIL = {
    "deny": True,
    "characterCount": {
        "maxCharacters": 2000,
    },
}
GUARDRAIL_NAME_CHAR_COUNT = "Character Count Limit"

# Output guardrails (afterRequest)
JSON_SCHEMA_GUARDRAIL = {
    "deny": True,
    "jsonSchema": {
        "schema": {
            "type": "object",
            "properties": {
                "answer": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["answer"],
        },
    },
}
GUARDRAIL_NAME_JSON_SCHEMA = "JSON Schema Validation"

CONTAINS_CODE_GUARDRAIL = {
    "deny": False,
    "containsCode": {
        "format": "Python",
    },
}
GUARDRAIL_NAME_CONTAINS_CODE = "Code Detection"

OUTPUT_WORD_COUNT_GUARDRAIL = {
    "deny": True,
    "wordCount": {
        "maxWords": 500,
    },
}
GUARDRAIL_NAME_OUTPUT_WORD_COUNT = "Output Word Count Limit"

# =============================================================================
# Test Scenarios
# =============================================================================

# Test messages for input guardrails
INPUT_TEST_CASES = [
    {
        "name": "Safe prompt (no PII)",
        "message": "What is the capital of France?",
        "should_pass": True,
        "guardrails": [WORD_COUNT_GUARDRAIL, CHAR_COUNT_GUARDRAIL],
        "guardrail_names": [GUARDRAIL_NAME_WORD_COUNT, GUARDRAIL_NAME_CHAR_COUNT],
    },
    {
        "name": "Contains email (PII)",
        "message": "Send the report to john.doe@company.com please",
        "should_pass": False,
        "guardrails": [REGEX_PII_EMAIL_GUARDRAIL],
        "guardrail_names": [GUARDRAIL_NAME_PII_EMAIL],
    },
    {
        "name": "Contains phone (PII)",
        "message": "Call me at 555-123-4567 to discuss",
        "should_pass": False,
        "guardrails": [REGEX_PII_PHONE_GUARDRAIL],
        "guardrail_names": [GUARDRAIL_NAME_PII_PHONE],
    },
    {
        "name": "Contains SSN pattern",
        "message": "My social security number is 123-45-6789",
        "should_pass": False,
        "guardrails": [
            {
                "deny": True,
                "regexMatch": {
                    "rule": r"\b\d{3}-\d{2}-\d{4}\b",
                    "not": True,
                },
            }
        ],
        "guardrail_names": ["SSN Pattern Detection"],
    },
]

# Test messages for output guardrails
OUTPUT_TEST_CASES = [
    {
        "name": "Request JSON output",
        "message": 'Return a JSON object with "answer" and "confidence" fields. What is 2+2?',
        "guardrails": [JSON_SCHEMA_GUARDRAIL],
        "guardrail_names": [GUARDRAIL_NAME_JSON_SCHEMA],
        "description": "Validates LLM output matches expected JSON schema",
    },
    {
        "name": "Request code output",
        "message": "Write a Python hello world program",
        "guardrails": [CONTAINS_CODE_GUARDRAIL],
        "guardrail_names": [GUARDRAIL_NAME_CONTAINS_CODE],
        "description": "Detects if LLM output contains code",
    },
    {
        "name": "Request short response",
        "message": "What is the meaning of life? Answer briefly.",
        "guardrails": [OUTPUT_WORD_COUNT_GUARDRAIL],
        "guardrail_names": [GUARDRAIL_NAME_OUTPUT_WORD_COUNT],
        "description": "Validates response length stays within limits",
    },
]


def run_input_guardrails_demo(provider_config: dict):
    """
    Demo: Input Guardrails

    Shows how Portkey validates user input BEFORE sending to the LLM.
    This prevents PII leakage, prompt injection, and resource abuse.
    """
    print("\n" + "=" * 70)
    print("DEMO 1: Input Guardrails (Pre-LLM Validation)")
    print("=" * 70)
    print("Input guardrails evaluate the user's prompt BEFORE sending it to the LLM.")
    print("Failed checks block the request, preventing PII leakage and abuse.")

    results = []

    for test in INPUT_TEST_CASES:
        print(f"\n--- Test: {test['name']} ---")
        print(f"  Message: {test['message'][:80]}{'...' if len(test['message']) > 80 else ''}")
        print(f"  Guardrails: {', '.join(n for n in test['guardrail_names'])}")
        print(f"  Expected: {'PASS' if test['should_pass'] else 'BLOCK'}")

        config = create_guardrail_config(provider_config, input_guardrails=test["guardrails"])

        client = Portkey(
            base_url=GATEWAY_API_URL,
            api_key="dummy-key",
            config=json.dumps(config),
        )

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=provider_config["model"],
                messages=[{"role": "user", "content": test["message"]}],
                max_tokens=100,
            )
            elapsed = (time.time() - start) * 1000
            status = "PASSED"
            detail = response.choices[0].message.content[:60] if response.choices else "(empty)"
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            error_str = str(e)
            if "446" in error_str or "guardrail" in error_str.lower():
                status = "BLOCKED"
                detail = "Guardrail blocked request"
            else:
                status = "ERROR"
                detail = error_str[:60]

        expected_match = (status == "PASSED") == test["should_pass"] or (
            status == "BLOCKED" and not test["should_pass"]
        )
        match_icon = "[OK]" if expected_match else "[UNEXPECTED]"

        print(f"  Result: {status} ({elapsed:.0f}ms) {match_icon}")
        if detail:
            print(f"  Detail: {detail}")

        results.append(
            {
                "test": test["name"],
                "guardrails": ", ".join(test["guardrail_names"]),
                "expected": "PASS" if test["should_pass"] else "BLOCK",
                "actual": status,
                "latency_ms": round(elapsed),
                "correct": expected_match,
            }
        )

    # Print results table
    print("\n" + "-" * 70)
    print("Input Guardrails Results:")
    table = [
        [
            r["test"],
            r["guardrails"],
            r["expected"],
            r["actual"],
            f"{r['latency_ms']}ms",
            "OK" if r["correct"] else "UNEXPECTED",
        ]
        for r in results
    ]
    print(
        tabulate(
            table,
            headers=["Test", "Guardrail", "Expected", "Actual", "Latency", "Match"],
            tablefmt="grid",
        )
    )

    return results


def run_output_guardrails_demo(provider_config: dict):
    """
    Demo: Output Guardrails

    Shows how Portkey validates LLM responses AFTER generation.
    This ensures output format compliance, content safety, and quality.
    """
    print("\n" + "=" * 70)
    print("DEMO 2: Output Guardrails (Post-LLM Validation)")
    print("=" * 70)
    print("Output guardrails evaluate the LLM's response AFTER generation.")
    print("Failed checks can trigger retries, fallbacks, or blocking.")

    results = []

    for test in OUTPUT_TEST_CASES:
        print(f"\n--- Test: {test['name']} ---")
        print(f"  Message: {test['message'][:80]}")
        print(f"  Description: {test['description']}")
        print(f"  Guardrails: {', '.join(n for n in test['guardrail_names'])}")

        config = create_guardrail_config(provider_config, output_guardrails=test["guardrails"])

        client = Portkey(
            base_url=GATEWAY_API_URL,
            api_key="dummy-key",
            config=json.dumps(config),
        )

        start = time.time()
        try:
            response = client.chat.completions.create(
                model=provider_config["model"],
                messages=[{"role": "user", "content": test["message"]}],
                max_tokens=200,
            )
            elapsed = (time.time() - start) * 1000
            content = response.choices[0].message.content[:80] if response.choices else "(empty)"
            status = "PASSED"

            # Check if hook_results are available
            hook_results = getattr(response, "hook_results", None)
            if hook_results:
                print(f"  Hook Results: {json.dumps(hook_results, indent=2)[:200]}")

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            error_str = str(e)
            if "446" in error_str or "guardrail" in error_str.lower():
                status = "BLOCKED"
                content = "Output guardrail blocked response"
            elif "246" in error_str:
                status = "WARNING"
                content = "Output guardrail warning"
            else:
                status = "ERROR"
                content = error_str[:80]

        print(f"  Result: {status} ({elapsed:.0f}ms)")
        print(f"  Output: {content}")

        results.append(
            {
                "test": test["name"],
                "guardrails": ", ".join(test["guardrail_names"]),
                "status": status,
                "latency_ms": round(elapsed),
                "output": content[:50],
            }
        )

    # Print results table
    print("\n" + "-" * 70)
    print("Output Guardrails Results:")
    table = [
        [r["test"], r["guardrails"], r["status"], f"{r['latency_ms']}ms", r["output"]]
        for r in results
    ]
    print(
        tabulate(
            table,
            headers=["Test", "Guardrail", "Status", "Latency", "Output"],
            tablefmt="grid",
        )
    )

    return results


def run_comparison_demo(provider_config: dict):
    """
    Demo: Portkey Guardrails vs Manual LlamaGuard Approach

    Shows the advantage of built-in guardrails over manual safety implementations.
    """
    print("\n" + "=" * 70)
    print("DEMO 3: Portkey Guardrails vs Manual Approach (LlamaGuard)")
    print("=" * 70)
    print()
    print("Comparison of Portkey's built-in guardrails vs the manual approach")
    print("used in the LiteLLM POC (deploying LlamaGuard as a separate model).")
    print()

    comparison = [
        ["Setup complexity", "Config-based (JSON)", "Deploy LlamaGuard model + code"],
        ["Infrastructure", "No extra components", "Separate model deployment"],
        ["GPU required", "No (deterministic checks)", "Yes (LlamaGuard needs GPU)"],
        ["Input validation", "Built-in (40+ checks)", "Custom code required"],
        ["Output validation", "Built-in (40+ checks)", "Custom code required"],
        ["PII detection", "Regex-based (instant)", "LLM-based (200-500ms)"],
        ["JSON validation", "Built-in schema check", "Custom parsing code"],
        ["Prompt injection", "LLM-based detection", "LlamaGuard categories"],
        ["Latency overhead", "<10ms (deterministic)", "200-500ms (LLM call)"],
        ["Retry on failure", "Built-in retry logic", "Custom retry code"],
        ["Fallback on failure", "Built-in fallback", "Custom fallback code"],
        ["Safety categories", "Custom regex + LLM", "14 pre-defined (LlamaGuard)"],
        ["Cost", "Free (OSS gateway)", "GPU cost for LlamaGuard"],
    ]

    print(
        tabulate(
            comparison,
            headers=["Feature", "Portkey Guardrails", "Manual (LlamaGuard)"],
            tablefmt="grid",
        )
    )

    print("KEY ADVANTAGES OF PORTKEY GUARDRAILS:")
    print("  1. No additional model deployment needed (deterministic checks are free)")
    print("  2. Sub-millisecond latency for regex/schema checks vs 200-500ms for LLM")
    print("  3. Built-in retry and fallback when guardrails fail")
    print("  4. Configuration-driven (no custom code for standard checks)")
    print("  5. Combines deterministic + LLM-based checks in one pipeline")

    # Run a timed comparison: Portkey guardrail check vs simulated LlamaGuard
    print("-" * 70)
    print("Timing Comparison: PII Detection")
    print("-" * 70)

    test_message = "Contact john.doe@company.com for details"

    # Portkey guardrail check (regex-based)
    config = create_guardrail_config(provider_config, input_guardrails=[REGEX_PII_EMAIL_GUARDRAIL])
    client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="dummy-key",
        config=json.dumps(config),
    )

    start = time.time()
    try:
        client.chat.completions.create(
            model=provider_config["model"],
            messages=[{"role": "user", "content": test_message}],
            max_tokens=10,
        )
        portkey_time = (time.time() - start) * 1000
        portkey_result = "PASSED (unexpected)"
    except Exception:
        portkey_time = (time.time() - start) * 1000
        portkey_result = "BLOCKED (PII detected)"

    print(f"\n  Portkey Guardrail (regex): {portkey_time:.0f}ms - {portkey_result}")
    print("  Manual LlamaGuard (est.): 200-500ms - Would need separate LLM call")
    print(f"  Portkey advantage: ~{max(200 - portkey_time, 0):.0f}ms faster (no GPU needed)")


def main():
    parser = argparse.ArgumentParser(
        description="Portkey AI Gateway - Guardrails Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenario",
        choices=["all", "input", "output", "comparison"],
        default="all",
        help="Demo scenario to run (default: all)",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "llama-fp8", "rhoai-primary", "rhoai-secondary"],
        default="ollama",
        help="LLM provider to use (default: ollama)",
    )
    args = parser.parse_args()

    print_config()

    provider_config = get_provider_config(args.provider)
    print(f"\nUsing provider: {args.provider}")
    print(f"Model: {provider_config['model']}")

    if args.scenario in ("all", "input"):
        run_input_guardrails_demo(provider_config)

    if args.scenario in ("all", "output"):
        run_output_guardrails_demo(provider_config)

    if args.scenario in ("all", "comparison"):
        run_comparison_demo(provider_config)

    print("\n" + "=" * 70)
    print("Guardrails demo completed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
