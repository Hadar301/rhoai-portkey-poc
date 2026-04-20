# Portkey AI Gateway - Load Balancing Demo

This demo showcases Portkey AI Gateway's load balancing capabilities, demonstrating how the gateway distributes requests across multiple LLM providers to optimize performance, reliability, and cost.

## Overview

The load balancing demo illustrates key distribution strategies:

- **Round-Robin Distribution**: Evenly distribute traffic across providers
- **Weighted Load Balancing**: Route traffic based on configurable weights (e.g., 70%-30%)
- **Multi-Provider Support**: Balance between different LLM providers (Ollama and LLaMA FP8)
- **Performance Optimization**: Leverage faster providers for improved response times

## Prerequisites

- Portkey AI Gateway deployed on OpenShift
- Ollama deployment accessible via gateway
- LLaMA FP8 (vLLM) deployment accessible via gateway
- Python 3.12+
- Required packages: `portkey-ai>=2.1.0`, `tabulate>=0.9.0`

## Installation

The demo is located in the `demos/load_balance` directory:

```bash
cd demos/load_balance
```

All dependencies are already defined in the project's `pyproject.toml`.

## Usage

### Run All Tests

```bash
uv run python load_balance_demo.py
```

### Run Specific Scenarios

```bash
# Test 1: Round-robin load balancing
uv run python load_balance_demo.py --scenario round-robin

# Test 2: Weighted load balancing
uv run python load_balance_demo.py --scenario weighted

# Test 3: Distribution analysis
uv run python load_balance_demo.py --scenario distribution
```

## Test Scenarios

### TEST 1: Round-Robin Load Balancing

**Objective**: Demonstrate even distribution of requests across multiple providers.

**Configuration**:
```python
{
  "strategy": {
    "mode": "loadbalance"
  },
  "targets": [
    {
      "provider": "ollama",
      "api_key": "dummy-key-not-needed",
      "custom_host": "http://portkey-gateway-ollama:11434",
      "weight": 0.5,
      "override_params": {"model": "llama3"}
    },
    {
      "provider": "openai",
      "api_key": "dummy-key-not-needed",
      "custom_host": "http://llama-fp8-predictor.hacohen-llmlite:8080/v1",
      "weight": 0.5,
      "override_params": {"model": "llama-fp8"}
    }
  ]
}
```

**Sample Output**:
```
======================================================================
TEST 1: Round-Robin Load Balancing
======================================================================

Configuration:
  Strategy: Round-Robin (Equal Weights)
  Targets:
    1. ollama - http://portkey-gateway-ollama:11434
    2. openai - http://llama-fp8-predictor.hacohen-llmlite:8080/v1

[Testing] Sending 6 requests with round-robin load balancing...

[Request 1/6] 'What is AI?...'
  SUCCESS: Artificial Intelligence (AI) refers to the development of co...
  Latency: 0.995s | Provider: openai

[Request 2/6] 'What is Python?...'
  SUCCESS: Python is a high-level, interpreted programming language tha...
  Latency: 0.941s | Provider: openai

[Request 3/6] 'What is Docker?...'
  SUCCESS: Docker is an open-source containerization platform that allo...
  Latency: 0.935s | Provider: openai

[Request 4/6] 'What is REST?...'
  SUCCESS: REST (Representational State of Resource) is a software arch...
  Latency: 20.834s | Provider: ollama

[Request 5/6] 'What is CI/CD?...'
  SUCCESS: CI/CD stands for Continuous Integration/Continuous Deploymen...
  Latency: 0.963s | Provider: openai

[Request 6/6] 'What is Kubernetes?...'
  SUCCESS: Kubernetes (abbreviated as K8s) is an open-source container ...
  Latency: 17.216s | Provider: ollama

  Statistics:
  - Total requests: 6
  - Successful: 6
  - Failed: 0
  - Success rate: 100.0%
  - Avg latency: 6.981s
  - Min/Max latency: 0.935s / 20.834s

  Provider Distribution:
    - openai: 4 requests (66.7%)
    - ollama: 2 requests (33.3%)
```

**Key Insights**:
- 100% success rate across both providers
- LLaMA FP8 (openai) is ~20x faster (~1s vs ~20s)
- Distribution shows 66.7% / 33.3% (small sample size variance)
- Load balancing works seamlessly across different provider types

---

### TEST 2: Weighted Load Balancing

**Objective**: Distribute requests based on configured weights to optimize for cost, performance, or capacity.

**Configuration**:
- Ollama: 25% of traffic
- LLaMA FP8: 75% of traffic

**Sample Output**:
```
======================================================================
TEST 2: Weighted Load Balancing
======================================================================

Configuration:
  Strategy: Weighted Load Balancing
  Targets:
    1. ollama - Weight: 0.25 (25%)
    2. openai - Weight: 0.75 (75%)

[Testing] Sending 10 requests with weighted load balancing...

[Request 1/10]
  SUCCESS: Latency: 0.946s | Provider: openai

[Request 2/10]
  SUCCESS: Latency: 17.743s | Provider: ollama

[Request 3/10]
  SUCCESS: Latency: 0.928s | Provider: openai

[Request 4/10]
  SUCCESS: Latency: 0.958s | Provider: openai

[Request 5/10]
  SUCCESS: Latency: 0.963s | Provider: openai

[Request 6/10]
  SUCCESS: Latency: 0.950s | Provider: openai

[Request 7/10]
  SUCCESS: Latency: 17.740s | Provider: ollama

[Request 8/10]
  SUCCESS: Latency: 0.951s | Provider: openai

[Request 9/10]
  SUCCESS: Latency: 0.922s | Provider: openai

[Request 10/10]
  SUCCESS: Latency: 17.664s | Provider: ollama

  Statistics:
  - Total requests: 10
  - Successful: 10
  - Failed: 0
  - Success rate: 100.0%
  - Avg latency: 5.976s

  Provider Distribution:
    - openai: 7 requests (70.0%)
    - ollama: 3 requests (30.0%)

  Expected Distribution:
    - ollama: 25%
    - openai: 75%
```

**Key Insights**:
- Actual distribution (70% / 30%) very close to expected (75% / 25%)
- Weighted balancing allows routing more traffic to faster/cheaper providers
- 100% success rate with mixed provider usage
- Average latency of 5.976s (optimized by using more of the faster provider)

---

### TEST 3: Load Distribution Analysis

**Objective**: Verify distribution accuracy with a larger sample size.

**Configuration**:
- Strategy: Round-Robin
- Number of requests: 20
- Expected distribution: 50% / 50%

**Sample Output**:
```
======================================================================
TEST 3: Load Distribution Analysis (20 Requests)
======================================================================

Configuration:
  Strategy: Round-Robin
  Targets: 2 providers (Ollama & LLaMA FP8)
  Expected Distribution: 50% / 50%

[Testing] Sending 20 quick requests...
  Progress: 5/20 requests sent...
  Progress: 10/20 requests sent...
  Progress: 15/20 requests sent...
  Progress: 20/20 requests sent...

  Results:
  - Total requests: 20
  - Successful: 20 (100.0%)
  - Avg latency: 4.277s

  Distribution Analysis:
    - openai: 6 requests (30.0%)
      Expected: 50% | Deviation: 20.0%
    - ollama: 14 requests (70.0%)
      Expected: 50% | Deviation: 20.0%
```

**Key Insights**:
- 100% success rate across 20 requests
- Distribution shows natural variance (30% / 70% vs expected 50% / 50%)
- Average latency of 4.277s
- Load balancing remains stable under multiple requests

---

## Results Summary

```
======================================================================
LOAD BALANCING DEMO RESULTS SUMMARY
======================================================================

Round-Robin Load Balancing:
  - Total Requests: 6
  - Success Rate: 100.0%
  - Avg Latency: 6.981s
  - Distribution: {'openai': 4, 'ollama': 2}

Weighted Load Balancing:
  - Total Requests: 10
  - Success Rate: 100.0%
  - Avg Latency: 5.976s
  - Distribution: {'openai': 7, 'ollama': 3}

Distribution Analysis:
  - Total Requests: 20
  - Success Rate: 100.0%
  - Avg Latency: 4.277s
  - Distribution: {'openai': 6, 'ollama': 14}

✓ Demo completed successfully!
======================================================================
```

## Configuration Details

### Portkey Load Balance Config Format

The demo uses Portkey's config object format to define load balancing strategies:

```python
config = {
    "strategy": {
        "mode": "loadbalance"
    },
    "targets": [
        {
            "provider": "ollama",
            "api_key": "dummy-key-not-needed",
            "custom_host": "http://portkey-gateway-ollama:11434",
            "weight": 0.5,  # 50% of traffic
            "override_params": {
                "model": "llama3"
            }
        },
        {
            "provider": "openai",
            "api_key": "dummy-key-not-needed",
            "custom_host": "http://llama-fp8-predictor.hacohen-llmlite:8080/v1",
            "weight": 0.5,  # 50% of traffic
            "override_params": {
                "model": "llama-fp8"
            }
        }
    ]
}
```

### Weight Configuration

Weights determine the proportion of traffic each provider receives:

```python
# Equal distribution (Round-Robin)
weights = [0.5, 0.5]  # 50% / 50%

# Weighted distribution (favor faster provider)
weights = [0.25, 0.75]  # 25% / 75%

# Three-way split
weights = [0.5, 0.3, 0.2]  # 50% / 30% / 20%
```

**Weight Normalization**: Weights are automatically normalized to sum to 1.0:
- Input: `[7, 3]` → Normalized: `[0.7, 0.3]`
- Input: `[5, 3, 1]` → Normalized: `[0.556, 0.333, 0.111]`

### Using the Config in Code

```python
from portkey_ai import Portkey
from load_balance.config import create_round_robin_config, create_weighted_config

# Round-robin configuration
config = create_round_robin_config([OLLAMA_CONFIG, LLAMA_FP8_CONFIG])

# Weighted configuration
config = create_weighted_config(
    targets=[OLLAMA_CONFIG, LLAMA_FP8_CONFIG],
    weights=[0.25, 0.75]
)

# Create client with load balancing
client = Portkey(
    base_url=GATEWAY_API_URL,
    api_key="not-needed-for-self-hosted",
    config=config
)

# Make request - Portkey automatically routes to providers based on weights
response = client.chat.completions.create(
    model="llama3",  # Model specified in override_params per provider
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100
)
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Portkey Gateway                      │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Load Balance Strategy Config             │  │
│  │  mode: "loadbalance"                             │  │
│  │  weights: [0.25, 0.75]                           │  │
│  └──────────────────────────────────────────────────┘  │
│                      │                                  │
│         ┌────────────┴─────────────┐                   │
│         ▼ 25%                 75% ▼                     │
│  ┌─────────────┐          ┌──────────────┐            │
│  │   Ollama    │          │  LLaMA FP8   │            │
│  │  (slower)   │          │  (faster)    │            │
│  │   ~20s      │          │    ~1s       │            │
│  └─────────────┘          └──────────────┘            │
└─────────────────────────────────────────────────────────┘
```

## Performance Comparison

### Provider Performance

| Provider | Avg Latency | Use Case |
|----------|-------------|----------|
| LLaMA FP8 (vLLM) | ~1s | Fast responses, high throughput |
| Ollama | ~20s | Lower resource usage, cost-effective |

### Load Balancing Strategies

| Strategy | Configuration | Best For |
|----------|--------------|----------|
| **Round-Robin** | Equal weights (0.5, 0.5) | Even distribution, simple setup |
| **Weighted** | Custom weights (0.25, 0.75) | Performance optimization, cost control |
| **Performance-First** | High weight to faster provider | Minimize latency |
| **Cost-First** | High weight to cheaper provider | Minimize costs |

## Key Takeaways

### ✓ Multi-Provider Load Balancing
- **100% success rate** across all tests
- Seamless routing between Ollama and LLaMA FP8 providers
- No code changes needed to switch providers

### ✓ Performance Optimization
- LLaMA FP8 provides **20x faster** responses (~1s vs ~20s)
- Weighted balancing optimizes average latency
- Route more traffic to faster providers for better UX

### ✓ Flexible Configuration
- **Round-robin**: Equal distribution for simplicity
- **Weighted**: Custom ratios for optimization
- **Automatic normalization**: Weights sum to 1.0

### ✓ Production Benefits
- **High availability**: Multiple providers for resilience
- **Cost optimization**: Route traffic based on cost/performance
- **Scalability**: Add providers without code changes
- **Performance**: Leverage fastest providers for critical requests

---

## Use Cases

### 1. Cost Optimization

Route majority of traffic to cost-effective provider, use premium for complex queries:

```python
weights = [0.8, 0.2]  # 80% cost-effective, 20% premium
```

### 2. Performance Optimization

Route majority to fastest provider for better user experience:

```python
weights = [0.2, 0.8]  # 20% slower, 80% faster
```

### 3. Capacity Management

Distribute based on provider capacity to prevent overload:

```python
weights = [0.3, 0.5, 0.2]  # Split across 3 providers based on capacity
```

### 4. Blue-Green Deployment

Test new provider with small percentage before full rollout:

```python
weights = [0.95, 0.05]  # 95% stable, 5% new provider
```

---

## Troubleshooting

### Requests Not Balanced

**Issue**: All requests going to one provider.

**Solutions**:
- Verify config includes multiple targets
- Check weights are set correctly
- Ensure all provider endpoints are reachable
- Review gateway logs for routing decisions

### Provider Failures

**Issue**: Requests failing for specific provider.

**Solutions**:
- Check provider endpoint is accessible from gateway
- Verify model names in `override_params` match provider
- Test provider directly with curl
- Combine with fallback strategy for resilience

### Uneven Distribution

**Issue**: Distribution doesn't match expected weights.

**Solutions**:
- Small sample sizes show natural variance
- Increase number of requests for accurate distribution
- Portkey uses probabilistic routing, not strict round-robin
- Distribution accuracy improves with larger samples

---

## Files

- `load_balance_demo.py` - Main demo script with CLI interface
- `config.py` - Load balancing configuration helpers
- `load_balance_demo.md` - This documentation file

## References

- [Portkey Load Balancing Documentation](https://portkey.ai/docs/product/ai-gateway/load-balancing)
- [Portkey Config Object Reference](https://portkey.ai/docs/api-reference/inference-api/config-object)
- [Portkey Python SDK](https://github.com/Portkey-AI/portkey-python-sdk)
- [Portkey Gateway GitHub](https://github.com/Portkey-AI/gateway)

## Next Steps

To extend this demo:

1. **Combine with Fallback**: Add fallback strategy for resilience
   ```python
   # Load balance with fallback
   config = {
       "strategy": {"mode": "loadbalance"},
       "targets": [
           {"provider": "ollama", "weight": 0.5, "fallback": "openai"},
           {"provider": "openai", "weight": 0.5, "fallback": "ollama"}
       ]
   }
   ```

2. **Sticky Sessions**: Route user sessions to same provider
   ```python
   "strategy": {
       "mode": "loadbalance",
       "sticky_session": {
           "hash_fields": ["metadata.user_id"],
           "ttl": 3600
       }
   }
   ```

3. **Dynamic Weights**: Adjust weights based on provider metrics
4. **Multi-Region**: Balance across geographically distributed providers
5. **A/B Testing**: Compare provider quality with controlled distribution

---

## Conclusion

The Portkey AI Gateway load balancing demo demonstrates **production-ready traffic distribution** across multiple LLM providers:

- ✓ **100% success rate** across all scenarios
- ✓ **Flexible strategies**: Round-robin and weighted balancing
- ✓ **Performance optimization**: ~20x faster with LLaMA FP8
- ✓ **Multi-provider support**: Seamless routing across Ollama and vLLM
- ✓ **Simple configuration**: No code changes, just config updates

Load balancing enables you to optimize for cost, performance, and reliability by intelligently distributing requests across your LLM infrastructure.
