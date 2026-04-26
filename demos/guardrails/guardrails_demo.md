# Portkey Guardrails Demo

## Overview

This demo showcases Portkey's built-in guardrails system, which is available in the **open-source gateway**. The OSS gateway includes ~15 deterministic guardrail checks (regex matching, JSON schema, word count, code detection, etc.). LLM-based checks (toxicity, prompt injection, gibberish detection) are available in the Enterprise/SaaS version.

## Guardrails vs LiteLLM/LlamaGuard

| Aspect | Portkey Guardrails | LiteLLM + LlamaGuard |
|--------|-------------------|---------------------|
| **Setup** | Config-based (JSON) | Deploy LlamaGuard model + custom code |
| **Infrastructure** | No extra components | Separate GPU-backed model |
| **PII Detection** | Regex-based (instant) | LLM-based (200-500ms) |
| **Latency** | <10ms (deterministic) | 200-500ms (LLM call) |
| **GPU Required** | No (deterministic) | Yes (LlamaGuard) |
| **Cost** | Free (OSS) | GPU compute cost |

## Demo Scenarios

### 1. Input Guardrails (Pre-LLM)

Validates user prompts **before** sending to the LLM:

- **PII Email Detection**: Blocks prompts containing email addresses (regexMatch)
- **PII Phone Detection**: Blocks prompts containing phone numbers (regexMatch)
- **SSN Pattern Detection**: Blocks prompts containing Social Security Number patterns (regexMatch)

**Note**: `wordCount` and `characterCount` checks do **not** work as input guardrails. They only evaluate response content in output guardrails.

### 2. Output Guardrails (Post-LLM)

Validates LLM responses **after** generation:

- **JSON Schema Validation**: Ensures output matches expected structure
- **Code Detection**: Detects if output contains code blocks
- **Word Count Limit**: Ensures response length stays within bounds

### 3. Comparison with LlamaGuard

Side-by-side comparison showing Portkey's advantages:
- No additional model deployment needed
- Sub-millisecond latency for deterministic checks
- Built-in retry and fallback on guardrail failure

## Running the Demo

```bash
# Run all scenarios
uv run python demos/guardrails/guardrails_demo.py

# Run specific scenario
uv run python demos/guardrails/guardrails_demo.py --scenario input
uv run python demos/guardrails/guardrails_demo.py --scenario output
uv run python demos/guardrails/guardrails_demo.py --scenario comparison

# Use RHOAI model
uv run python demos/guardrails/guardrails_demo.py --provider rhoai-primary
```

## Available Guardrail Checks

Check IDs use **camelCase** in the config (e.g., `regexMatch`, not `regex_match`).

### Deterministic (No LLM needed)

| Check ID | Description | Notes |
|----------|-------------|-------|
| `regexMatch` | Match/block content using regex patterns | Set `"not": true` to block when regex matches (e.g., PII detection) |
| `containsCode` | Detect code in input/output | |
| `wordCount` | Enforce word count limits | **Output guardrails only** - does not work as input guardrail |
| `characterCount` | Enforce character count limits | **Output guardrails only** - does not work as input guardrail |
| `sentenceCount` | Enforce sentence count limits | |
| `jsonSchema` | Validate JSON against schema | |
| `jsonKeys` | Validate required JSON keys | |
| `validUrls` | Validate URL format | |
| `contains` | Check if content contains specific strings | |
| `alluppercase` | Check if content is all uppercase | |
| `alllowercase` | Check if content is all lowercase | |
| `endsWith` | Check if content ends with specific string | |
| `modelWhitelist` | Restrict allowed models | |
| `notNull` | Ensure content is not null/empty | |

### LLM-Based (Requires LLM call, SaaS/Enterprise)

| Check ID | Description |
|----------|-------------|
| `gibberish` | Detect gibberish/nonsensical content |
| `prompt_injection` | Detect prompt injection attempts |
| `language` | Detect/enforce language constraints |
| `pii` | Advanced PII detection (names, addresses) |
| `toxicity` | Detect toxic/harmful content |

## Guardrail Config Format

Each guardrail is a dict with reserved keys and check definitions:

```python
{
    "deny": True,           # Block request on failure (HTTP 446)
    "regexMatch": {         # Check ID (camelCase)
        "rule": r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
        "not": True,        # Invert: block when regex DOES match
    },
}
```

**Reserved keys**: `deny`, `async`, `on_fail`, `on_success`, `id`, `type`
**Everything else** is treated as a check ID with its parameter object.

## Guardrail Behavior

| `deny` value | On check failure | HTTP Status |
|--------------|-----------------|-------------|
| `true` | Block request immediately | 446 |
| `false` | Allow request, log result | 200 |
