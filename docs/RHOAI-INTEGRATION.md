# RHOAI Integration Guide

## Overview

This guide explains how to integrate the Portkey AI Gateway with Red Hat OpenShift AI (RHOAI) models deployed via KServe.

## Architecture

```
Portkey Gateway (portkey-gateway namespace)
    │
    │  OpenAI-compatible API
    ▼
KServe InferenceService (rhoai-models namespace)
    │
    │  vLLM runtime
    ▼
GPU Node (model inference)
```

## Prerequisites

1. RHOAI installed on your OpenShift cluster
2. At least one model deployed as a KServe InferenceService
3. Portkey gateway deployed (using the Helm chart in this repo)

### Prerequisites Verification

```bash
# Verify OpenShift cluster access
oc get nodes

# Verify RHOAI installation
oc get operators -A | grep rhods

# Verify KServe models are deployed and ready
oc get inferenceservices -A

# Verify Portkey gateway is running
oc get pods -l app.kubernetes.io/name=portkey-gateway
oc get routes -l app.kubernetes.io/name=portkey-gateway

# Check gateway health
curl -I "https://$(oc get route portkey-gateway -o jsonpath='{.spec.host}')/health"
```

## Step 1: Identify RHOAI Model Endpoints

List your KServe InferenceServices:

```bash
oc get inferenceservices -n <rhoai-namespace> -o custom-columns=\
  NAME:.metadata.name,\
  URL:.status.url,\
  READY:.status.conditions[?\(@.type==\"Ready\"\)].status
```

**Important**: The Portkey gateway rejects fully-qualified domain names (FQDNs) ending in `.svc.cluster.local` as "Invalid custom host". This limitation affects cross-namespace access.

**Same-namespace access**: Use short service names when the gateway and model are in the same namespace:
```
http://<service-name>:8080/v1
```

**Cross-namespace access**: Use either:
1. Short service names if DNS resolution works: `http://model-name:8080/v1`
2. FQDNs without `.svc.cluster.local` suffix require NetworkPolicy egress rules
3. See [Known Issues in summary.md](../summary.md#known-issues) for networking limitations

## Step 2: Configure Portkey

### Option A: Environment Variables

Set environment variables before running demos:

```bash
# Same-namespace models (use short service names)
export RHOAI_VLLM_PRIMARY_HOST="http://llama-32-1b-fp8-metrics:8080/v1"
export RHOAI_VLLM_PRIMARY_MODEL="llama-32-1b-fp8"
export RHOAI_VLLM_SECONDARY_HOST="http://mistral-7b-predictor:8080/v1"
export RHOAI_VLLM_SECONDARY_MODEL="mistralai/Mistral-7B-Instruct-v0.2"
```

### Option B: Edit demos/config.py

Update the RHOAI configuration section directly in [demos/config.py](../demos/config.py):

```python
RHOAI_VLLM_PRIMARY_CONFIG = {
    "provider": "openai",
    "custom_host": "http://llama-32-1b-fp8-metrics:8080/v1",  # Short service name
    "model": "llama-32-1b-fp8",
}
```

## Step 3: Verify Connectivity

```bash
uv run python demos/rhoai/connectivity_test.py --provider rhoai-primary
```

## Step 4: Run Demos with RHOAI Models

All demos support the `--provider` flag:

```bash
# Fallback demo with RHOAI primary
uv run python demos/fallback/fallback_demo.py --provider rhoai-primary

# Load balancing between RHOAI models
uv run python demos/load_balance/load_balance_demo.py --provider rhoai-primary

# Guardrails with RHOAI
uv run python demos/guardrails/guardrails_demo.py --provider rhoai-primary
```

## Networking

### Custom Host Limitation

The Portkey gateway validates `custom_host` values and rejects fully-qualified domain names (FQDNs) containing `.svc.cluster.local`. Use short service names:

```python
# Correct (short service name)
"custom_host": "http://llama-32-1b-fp8-metrics:8080/v1"

# Incorrect (FQDN - rejected by gateway)
"custom_host": "http://llama-32-1b-fp8-metrics.your-namespace.svc.cluster.local:8080/v1"
```

### Authentication

KServe vLLM endpoints typically don't require authentication within the cluster. If your RHOAI deployment uses authentication tokens, pass them via the `api_key` field in the provider config:

```python
RHOAI_CONFIG = {
    "provider": "openai",
    "custom_host": "http://llama-32-1b-fp8-metrics:8080/v1",
    "model": "llama-32-1b-fp8",
    "api_key": "<your-token>",  # If auth is enabled
}
```

## Troubleshooting

For comprehensive RHOAI troubleshooting, see **[TROUBLESHOOTING.md](../TROUBLESHOOTING.md#rhoai-integration-issues)**.

### Quick Diagnostics

```bash
# Verify InferenceService status
oc get inferenceservice -n rhoai-models

# Test model endpoint directly
curl http://model-service:8080/v1/models

# Test gateway to model connectivity
oc exec -n portkey-gateway deploy/portkey-gateway -- \
  curl -s http://llama-32-1b-fp8-metrics:8080/v1/models
```

**Common issues**: FQDN rejection, cross-namespace networking, model name mismatches. See the main troubleshooting guide for detailed solutions.
