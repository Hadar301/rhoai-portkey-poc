# Portkey AI Gateway for OpenShift (RHOAI)

Deploy the open-source [Portkey AI Gateway](https://github.com/Portkey-AI/gateway) on Red Hat OpenShift with optional local LLM support via Ollama.

## Overview

The Portkey AI Gateway is an open-source AI gateway that routes requests to 250+ LLMs with features like:

- **Unified API**: Single interface for OpenAI, Anthropic, Azure, Google, Cohere, Ollama, and more
- **Load Balancing**: Distribute requests across multiple providers
- **Fallbacks**: Automatic failover to backup providers
- **Retries**: Configurable retry logic with exponential backoff
- **Caching**: Redis-backed response caching
- **Local LLM**: Optional Ollama deployment for local inference

## Prerequisites

- OpenShift cluster (4.x+)
- Helm 3.x
- `oc` CLI configured with cluster access

## Quick Start

### Option 1: Using the Install Script (Recommended)

```bash
cd portkey

# Install with Ollama (default)
./install.sh hacohen-portkey

# Install without Ollama
./install.sh hacohen-portkey --no-ollama

# Install with a specific model
./install.sh hacohen-portkey --model mistral
```

### Option 2: Using Make

```bash
cd portkey
make helm-install NAMESPACE=hacohen-portkey
```

### Option 3: Manual Helm Install

```bash
cd portkey/helm
helm dependency update
helm upgrade --install portkey-gateway . \
  --namespace hacohen-portkey \
  --create-namespace \
  -f values.yaml
```

## Uninstall

```bash
cd portkey

# Uninstall (keep namespace)
./uninstall.sh hacohen-portkey

# Uninstall and delete namespace
./uninstall.sh hacohen-portkey --delete-namespace

# Force uninstall (skip confirmation)
./uninstall.sh hacohen-portkey --force
```

## Using the Gateway

### With External Providers (OpenAI, etc.)

```bash
GATEWAY_URL=$(oc get route portkey-gateway -n hacohen-portkey -o jsonpath='{.spec.host}')

curl -X POST "https://${GATEWAY_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "x-portkey-provider: openai" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### With Ollama (Local LLM)

```bash
GATEWAY_URL=$(oc get route portkey-gateway -n hacohen-portkey -o jsonpath='{.spec.host}')

curl -X POST "https://${GATEWAY_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "x-portkey-provider: ollama" \
  -H "x-portkey-custom-host: http://portkey-gateway-ollama:11434" \
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Configuration

### Key Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of gateway replicas | `2` |
| `image.repository` | Gateway image | `portkeyai/gateway` |
| `route.enabled` | Create OpenShift Route | `true` |
| `redis.enabled` | Deploy Redis for caching | `true` |
| `ollama.enabled` | Deploy Ollama for local LLM | `true` |
| `ollama.model` | Ollama model to pull | `llama3` |
| `autoscaling.enabled` | Enable HPA | `true` |

### API Keys

Configure LLM provider API keys in `values.yaml`:

```yaml
secrets:
  openaiApiKey: "sk-..."
  anthropicApiKey: "sk-ant-..."
```

### Ollama Models

Available models include:
- `llama3` - Meta's Llama 3 (default)
- `mistral` - Mistral 7B
- `codellama` - Code Llama
- `phi` - Microsoft Phi-2

To change the model:
```bash
helm upgrade portkey-gateway helm/ -n hacohen-portkey --set ollama.model=mistral
```

## Scripts

| Script | Description |
|--------|-------------|
| `install.sh` | Install Portkey Gateway with Ollama |
| `uninstall.sh` | Uninstall Portkey Gateway |

### Install Script Options

```bash
./install.sh [NAMESPACE] [OPTIONS]

Options:
  --no-ollama    Skip Ollama deployment
  --model NAME   Specify Ollama model (default: llama3)
```

### Uninstall Script Options

```bash
./uninstall.sh [NAMESPACE] [OPTIONS]

Options:
  --delete-namespace    Also delete the namespace
  --force, -f           Skip confirmation prompt
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make helm-deps` | Download chart dependencies |
| `make helm-install` | Install the chart |
| `make helm-upgrade` | Upgrade existing release |
| `make helm-uninstall` | Remove the release |
| `make oc-pods` | List all pods |
| `make oc-logs` | Tail gateway logs |
| `make oc-route` | Get route URL |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OpenShift Cluster                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Namespace: hacohen-portkey              │   │
│  │                                                      │   │
│  │   ┌─────────────┐     ┌─────────────────────────┐   │   │
│  │   │   Route     │────▶│  Portkey Gateway (x2)   │   │   │
│  │   └─────────────┘     └───────────┬─────────────┘   │   │
│  │                                   │                  │   │
│  │         ┌─────────────────────────┼──────────┐      │   │
│  │         ▼                         ▼          ▼      │   │
│  │   ┌──────────┐           ┌──────────┐  ┌─────────┐  │   │
│  │   │  Redis   │           │  Ollama  │  │External │  │   │
│  │   │ (cache)  │           │ (llama3) │  │  LLMs   │  │   │
│  │   └──────────┘           └──────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Chart Structure

```
portkey/
├── install.sh              # Installation script
├── uninstall.sh            # Uninstallation script
├── MakeFile                # Make commands
└── helm/
    ├── Chart.yaml          # Chart metadata
    ├── values.yaml         # Default values
    └── templates/
        ├── deployment.yaml       # Gateway deployment
        ├── service.yaml          # Gateway service
        ├── route.yaml            # OpenShift Route
        ├── hpa.yaml              # Horizontal Pod Autoscaler
        ├── ollama-deployment.yaml # Ollama deployment
        ├── ollama-service.yaml    # Ollama service
        └── ...
```

## Resources

- [Portkey AI Documentation](https://portkey.ai/docs)
- [Portkey Gateway GitHub](https://github.com/Portkey-AI/gateway)
- [Portkey Helm Charts](https://github.com/Portkey-AI/helm)
- [Ollama Models](https://ollama.ai/library)

## License

See [LICENSE](LICENSE) for details.
