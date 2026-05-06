# Portkey AI Gateway for OpenShift (RHOAI)

Deploy the open-source [Portkey AI Gateway](https://github.com/Portkey-AI/gateway) on Red Hat OpenShift with RHOAI integration and production-ready features.

## Documentation Reading Guide

**Recommended order** for new users:
1. **Overview & Quick Start** (this file) - Start here for installation and basic concepts
2. **[RHOAI Integration](docs/RHOAI-INTEGRATION.md)** - If connecting to RHOAI KServe models
3. **[Comparison Matrix](docs/COMPARISON-MATRIX.md)** - If evaluating vs LiteLLM
4. **[Summary Report](summary.md)** - For known issues and production deployment guidance
5. **Demo Documentation** - Feature-specific guides linked below

## Overview

The Portkey AI Gateway is an open-source AI gateway that routes requests to 250+ LLMs with features like:

- **Unified API**: Single interface for OpenAI, Anthropic, Azure, Google, Cohere, Ollama, and more
- **Load Balancing**: Distribute requests across multiple providers
- **Fallbacks**: Automatic failover to backup providers
- **Caching**: Redis-backed response caching (simple + semantic)
- **Guardrails**: Built-in input/output validation checks (regex, schema, word count, code detection)
- **RHOAI Integration**: Route to KServe-deployed models via OpenAI-compatible API
- **Production Ready**: HA deployment, NetworkPolicy, PodDisruptionBudget

> **Important**: Many advanced features (Prometheus metrics, semantic caching, 60+ guardrails, admin dashboard) are **Enterprise-only** and not available in the OSS gateway. See [Enterprise-Only Features](#enterprise-only-features-not-available-in-oss) for details. All demos use OSS-compatible features only.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster                        │
│                                                             │
│  ┌───────────────── portkey-gateway ────────────────────┐   │
│  │                                                      │   │
│  │  ┌────────────┐     ┌────────────────────────────-┐  │   │
│  │  │ OpenShift  │────>│ Portkey Gateway (HA: 1+)    │  │   │
│  │  │ Route(TLS) │     │ + HPA (1-10 replicas)       │  │   │
│  │  └────────────┘     │ + Guardrails pipeline       │  │   │
│  │                     └──────┬──────────────────────┘  │   │
│  │                            │                         │   │
│  │      ┌─────────────────────┼────────────┐            │   │
│  │      v                     v            v            │   │
│  │  ┌────────┐         ┌──────────┐  ┌─────────┐        │   │
│  │  │ Redis  │         │ Ollama   │  │External │        │   │
│  │  │(cache) │         │(optional)│  │  LLMs   │        │   │
│  │  └────────┘         └──────────┘  └─────────┘        │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           │ KServe (OpenAI-compatible)      │
│                           v                                 │
│  ┌───────────────── rhoai-models ────────────────────────┐  │
│  │  ┌─────────────────┐     ┌─────────────────┐          │  │
│  │  │ vLLM Model 1    │     │ vLLM Model 2    │          │  │
│  │  │ (KServe)        │     │ (KServe)        │          │  │
│  │  └─────────────────┘     └─────────────────┘          │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- OpenShift cluster (4.x+)
- Helm 3.x
- `oc` CLI configured with cluster access
- (Optional) RHOAI with KServe models deployed

## Quick Start

### Option 1: Using the Install Script (Recommended)

```bash
cd portkey

# Install with Ollama (default)
./install.sh your-namespace

# Install without Ollama
./install.sh your-namespace --no-ollama

# Install with a specific model
./install.sh your-namespace --model mistral
```

### Option 2: Using Make

```bash
cd portkey
make helm-install NAMESPACE=your-namespace
```

### Option 3: Manual Helm Install

```bash
cd portkey/helm
helm dependency update
helm upgrade --install portkey-gateway . \
  --namespace your-namespace \
  --create-namespace \
  -f values.yaml
```

## Uninstall

```bash
cd portkey

# Uninstall (keep namespace)
./uninstall.sh your-namespace

# Uninstall and delete namespace
./uninstall.sh your-namespace --delete-namespace
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of gateway replicas | `1` |
| `image.repository` | Gateway image | `portkeyai/gateway` |
| `route.enabled` | Create OpenShift Route | `true` |
| `redis.enabled` | Deploy Redis for caching | `true` |
| `ollama.enabled` | Deploy Ollama for local LLM | `true` |
| `ollama.model` | Ollama model to pull | `llama3` |
| `autoscaling.enabled` | Enable HPA | `true` |
| `autoscaling.minReplicas` | Minimum replicas | `1` |
| `networkPolicy.enabled` | Create NetworkPolicy | `false` |
| `podDisruptionBudget.enabled` | Create PDB | `true` |

### RHOAI Integration

To connect to RHOAI-deployed models, see [docs/RHOAI-INTEGRATION.md](docs/RHOAI-INTEGRATION.md). RHOAI integration is handled at the demo/SDK level via the `custom_host` parameter, not through the Helm chart.

### API Keys

Configure LLM provider API keys in `values.yaml`:

```yaml
secrets:
  openaiApiKey: "sk-..."
  anthropicApiKey: "sk-ant-..."
```

## Demos

### Demo Selection Guide

**For resilience and reliability:**
- Start with **[Fallback Demo](demos/fallback/fallback_demo.md)** - Learn automatic failover
- Then try **[Load Balancing Demo](demos/load_balance/load_balance_demo.md)** - Distribute traffic for performance

**For performance optimization:**
- **[Redis Caching Demo](demos/caching/redis_caching_demo.md)** - 12.8x speedup with exact-match caching
- **[Semantic Caching Demo](demos/caching/semantic_caching_demo.md)** - 67% hit rate on paraphrased queries

**For safety and compliance:**
- **[Guardrails Demo](demos/guardrails/guardrails_demo.md)** - Block PII, validate schemas, detect code

**For RHOAI integration:**
- **[RHOAI Connectivity Test](demos/rhoai/connectivity_test.py)** - Verify KServe model access

### Available Demos

| Demo | Description | Command |
|------|-------------|---------|
| **Fallback** | Automatic failover between providers | `uv run python demos/fallback/fallback_demo.py` |
| **Load Balancing** | Weighted request distribution | `uv run python demos/load_balance/load_balance_demo.py` |
| **Redis Caching** | Exact-match response caching | `uv run python demos/caching/redis_caching_demo.py` |
| **Semantic Caching** | Similarity-based cache matching | `uv run python demos/caching/semantic_caching_demo.py` |
| **Guardrails** | Input/output validation (PII, schema) | `uv run python demos/guardrails/guardrails_demo.py` |
| **RHOAI Connectivity** | Test RHOAI model connectivity | `uv run python demos/rhoai/connectivity_test.py` |

### Environment Variables and Configuration

The demo configuration flows from multiple sources in this order of precedence:

1. **Environment variables** (highest priority) - Override all other settings
2. **`demos/config.py`** - Default provider configurations  
3. **Command-line flags** - Provider selection and scenarios

#### Configuration Setup

**Quick Start - Copy the example configuration:**
```bash
# Copy environment template and customize with your values
cp .env.example .env
# Edit .env with your specific cluster/namespace details
```

**Or set variables manually:**
```bash
# Install Python dependencies first
uv sync

# Required: Gateway access (for all demos)
export PORTKEY_GATEWAY_URL="https://$(oc get route portkey-gateway -o jsonpath='{.spec.host}')/v1"

# Required: Demo namespace 
export DEMO_NAMESPACE="your-namespace"  # Namespace where Portkey gateway is deployed

# Required for caching demos: Redis access
export REDIS_PASSWORD=$(oc get secret portkey-gateway-redis -o jsonpath='{.data.redis-password}' | base64 -d)
export REDIS_HOST="redis-service"  # Or use actual service name from your deployment

# Optional: Override service endpoints (if different from defaults)
export OLLAMA_SERVICE_HOST="http://your-ollama-service:11434"
export VLLM_SERVICE_HOST="http://your-vllm-service:8080/v1"

# Optional: RHOAI integration (required only if using --provider rhoai-primary)
export RHOAI_VLLM_PRIMARY_HOST="http://your-model-service:8080/v1"  # Use short service names
export RHOAI_VLLM_PRIMARY_MODEL="your-model-name"

# Verify connectivity
curl -X POST "$PORTKEY_GATEWAY_URL/chat/completions" -H "Content-Type: application/json" \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'
```

> **Note**: All configuration values have sensible defaults. See [.env.example](.env.example) for complete configuration options and examples.

#### Running Demos
```bash
# Basic demo (uses Ollama by default)
uv run python demos/guardrails/guardrails_demo.py --scenario all --provider ollama

# Using RHOAI models (requires RHOAI_* environment variables)
uv run python demos/fallback/fallback_demo.py --provider rhoai-primary

# Multiple scenarios
uv run python demos/caching/redis_caching_demo.py  # Requires REDIS_PASSWORD
```

### Using RHOAI Models in Demos

All demos support the `--provider` flag:

```bash
# Set RHOAI model endpoints (use short service names, not FQDNs)
export RHOAI_VLLM_PRIMARY_HOST="http://your-model-service:8080/v1"  # Replace with your actual model service name
export RHOAI_VLLM_PRIMARY_MODEL="your-model-name"  # Replace with your actual model name
# Example: export RHOAI_VLLM_PRIMARY_HOST="http://llama-32-1b-fp8-metrics:8080/v1"
# Example: export RHOAI_VLLM_PRIMARY_MODEL="llama-32-1b-fp8"

# Run with RHOAI provider
uv run python demos/guardrails/guardrails_demo.py --provider rhoai-primary
```

> **Important**: The Portkey gateway rejects fully-qualified domain names (FQDNs) ending in `.svc.cluster.local` as "Invalid custom host". This limitation affects cross-namespace access. Use short Kubernetes service names when connecting to models in the same namespace. See [RHOAI Integration Guide](docs/RHOAI-INTEGRATION.md) for cross-namespace workarounds.

## Production Features

### High Availability
- Default 1 replica with HPA (1-10)
- Pod anti-affinity for multi-node distribution
- PodDisruptionBudget (minAvailable: 1)

### Security
- NetworkPolicy template included (disabled by default due to OpenShift DNS compatibility; see [summary.md](summary.md))
- Non-root containers with restricted-v2 SCC
- Read-only root filesystem
- All capabilities dropped

### Guardrails (Built-in)
- Deterministic checks: regex matching, JSON schema validation, word/character/sentence count, code detection, URL validation
- Input guardrails (pre-LLM validation)
- Output guardrails (post-LLM validation)
- `deny: true` blocks requests (HTTP 446), `deny: false` allows with logging

## Portkey vs LiteLLM

For a detailed comparison, see [docs/COMPARISON-MATRIX.md](docs/COMPARISON-MATRIX.md).

**Portkey OSS strengths**: Built-in deterministic guardrails (~15 checks), lighter deployment (no PostgreSQL), wider provider support (250+).

**LiteLLM strengths**: Budget enforcement, admin dashboard (OSS), team management, rich observability integrations (Langfuse, Phoenix, etc.).

## Chart Structure

```
portkey/
├── install.sh                    # Installation script
├── uninstall.sh                  # Uninstallation script
├── MakeFile                      # Make commands
└── helm/
    ├── Chart.yaml                # Chart metadata
    ├── values.yaml               # Default values
    └── templates/
        ├── deployment.yaml              # Gateway deployment
        ├── service.yaml                 # Gateway service
        ├── route.yaml                   # OpenShift Route
        ├── hpa.yaml                     # Horizontal Pod Autoscaler
        ├── configmap.yaml               # Environment config
        ├── secrets.yaml                 # API keys
        ├── serviceaccount.yaml          # Service account
        ├── networkpolicy.yaml           # Network security
        ├── poddisruptionbudget.yaml     # HA disruption budget
        ├── ollama-deployment.yaml       # Ollama deployment
        ├── ollama-service.yaml          # Ollama service
        └── ollama-pvc.yaml              # Ollama storage
```

## Documentation

| Document | Description |
|----------|-------------|
| [RHOAI Integration](docs/RHOAI-INTEGRATION.md) | How to connect to RHOAI KServe models |
| [Comparison Matrix](docs/COMPARISON-MATRIX.md) | Portkey vs LiteLLM feature comparison |
| [Troubleshooting Guide](TROUBLESHOOTING.md) | Common issues and solutions across all components |
| [Summary Report](summary.md) | POC status, test results, and known issues |
| [Guardrails Demo](demos/guardrails/guardrails_demo.md) | Guardrails demo documentation |
| [Semantic Caching](demos/caching/semantic_caching_demo.md) | Semantic caching demo documentation |

## Enterprise-Only Features (Not Available in OSS)

The following Portkey features require the **Enterprise/SaaS** version and are **not included** in the open-source `portkeyai/gateway` image used in this POC:

| Feature | Description | OSS Alternative |
|---------|-------------|-----------------|
| **Prometheus Metrics** | `/metrics` endpoint for monitoring (15+ metrics) | None — gateway v1.15.x has no metrics support |
| **Semantic Caching** | Embedding-based similarity matching for cache hits | Custom implementation (demonstrated in this POC using Ollama embeddings via the gateway) |
| **60+ Guardrails** | LLM-based and advanced guardrail checks (PII with LLM, toxicity, prompt injection) | OSS has ~15 deterministic checks (regex, schema, word count, code detection) |
| **Prompt Management Studio** | Web UI for prompt versioning, A/B testing, collaboration | None |
| **Admin Dashboard** | Web UI for managing keys, teams, usage | None |
| **Budget Management** | Per-key/team/org spend limits and tracking | None |
| **Request Tracing** | Detailed execution path tracing for debugging | None |
| **Compliance Certifications** | SOC-2, ISO 27001, HIPAA, GDPR | None |
| **Pre-built Grafana Dashboards** | Ready-to-use observability dashboards | None |

All demos in this POC use only features available in the OSS gateway. The semantic caching demo uses Ollama embeddings (routed through the Portkey gateway) to implement the concept without requiring the Enterprise version.

## Resources

- [Portkey AI Documentation](https://portkey.ai/docs)
- [Portkey Gateway GitHub](https://github.com/Portkey-AI/gateway)
- [RHOAI LiteLLM POC](https://github.com/RHEcosystemAppEng/rhoai-litellm-poc) (reference implementation)
- [Ollama Models](https://ollama.ai/library)

## License

See [LICENSE](LICENSE) for details.
