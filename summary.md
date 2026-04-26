# Portkey AI Gateway for RHOAI - POC Summary

## Objective

Evaluate the Portkey AI Gateway as an alternative/complement to LiteLLM for managing LLM traffic in Red Hat OpenShift AI (RHOAI) environments. The POC builds on an existing Portkey deployment and enhances it with production-ready features, RHOAI integration, and comprehensive demos.

Reference implementation: [rhoai-litellm-poc](https://github.com/RHEcosystemAppEng/rhoai-litellm-poc)

## Planned vs Achieved

### Phase 1: Helm Chart Production Hardening

| Deliverable | Status | Notes |
|-------------|--------|-------|
| ServiceMonitor for Prometheus scraping | Removed | Removed — OSS gateway v1.15.x has no `/metrics` endpoint. Enterprise-only feature. |
| NetworkPolicy for traffic control | Partial | Created but disabled (`enabled: false`) due to DNS resolution issues with OpenShift CoreDNS ClusterIP. See [Known Issues](#known-issues). |
| PodDisruptionBudget (HA) | Achieved | `templates/poddisruptionbudget.yaml`, minAvailable: 1 |
| HPA with autoscaling | Achieved | Min 1, max 10 replicas. HPA active on cluster. |
| Grafana dashboard (12 panels) | Removed | Removed — no metrics data to display without Prometheus support. Enterprise-only feature. |
| PrometheusRule alert rules | Removed | Removed — no metrics to alert on. Enterprise-only feature. |
| Updated values.yaml with production defaults | Achieved | HA, security sections added |

### Phase 2: RHOAI Integration

| Deliverable | Status | Notes |
|-------------|--------|-------|
| KServe endpoint configuration | Achieved | `demos/config.py` configured for vLLM models via OpenAI-compatible API |
| Connectivity validation script | Achieved | `demos/rhoai/connectivity_test.py` - tested successfully |
| RHOAI integration documentation | Achieved | `docs/RHOAI-INTEGRATION.md` |
| Cross-namespace NetworkPolicy egress | Removed | RHOAI egress rule removed from Helm chart. NetworkPolicy is disabled by default; cross-namespace access works without it. |

### Phase 3: Guardrails Demo

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Input guardrails demo (PII blocking) | Achieved | 4/4 tests pass: email, phone, SSN regex blocking + safe prompt pass-through |
| Output guardrails demo | Achieved | JSON schema validation, code detection, word count limit |
| Comparison with LlamaGuard approach | Achieved | Timing comparison showing sub-ms Portkey checks vs LLM-based overhead |
| Documentation | Achieved | `demos/guardrails/guardrails_demo.md` |

### Phase 4: Semantic Caching Demo

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Custom semantic cache implementation | Achieved | Real embeddings from Ollama via Portkey gateway (`/v1/embeddings`) with cosine similarity |
| Comparison with exact-match caching | Achieved | Side-by-side results table comparing semantic vs exact-match on paraphrased queries |
| Documentation | Achieved | `demos/caching/semantic_caching_demo.md` |

### Phase 5: Enterprise Observability Demo

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Grafana dashboard JSON | Removed | Removed from codebase — OSS gateway has no Prometheus metrics support. Enterprise-only feature. |
| Prometheus alert rules | Removed | Removed from codebase — same reason as above. |
| Live demo script | Removed | `demos/observability/` directory removed — cannot demonstrate without metrics endpoint. |
| Prometheus /metrics endpoint | Not available | Gateway v1.15.x **does not include Prometheus metrics support**. This is an Enterprise-only feature. |

### Phase 6: Prompt Management Demo

| Deliverable | Status | Notes |
|-------------|--------|-------|
| Prompt management demo | Removed | Portkey Prompt Management Studio is **SaaS/Enterprise-only**. The OSS gateway has no prompt management functionality. Documentation-only deliverables (ConfigMap examples) were removed as they cannot be demonstrated against the live gateway. |

### Phase 7: Integration & Documentation

| Deliverable | Status | Notes |
|-------------|--------|-------|
| README.md | Achieved | Full project README with architecture, quick start, configuration |
| Comparison matrix (Portkey vs LiteLLM) | Achieved | `docs/COMPARISON-MATRIX.md` with detailed feature table |
| RHOAI integration guide | Achieved | `docs/RHOAI-INTEGRATION.md` |
| Demo documentation (per demo) | Achieved | 6 demo .md files covering all runnable scenarios |

## Demo Test Results

All demos were tested against a live OpenShift cluster.

| Demo | Result | Details |
|------|--------|---------|
| **Connectivity Test** | PASS | rhoai-primary (llama-32-1b-fp8) and ollama reachable. rhoai-secondary (mistral-7b) correctly fails (not deployed). |
| **Fallback** | PASS | Automatic failover from invalid endpoint to working provider. 100% success rate. |
| **Load Balancing** | PASS | Round-robin, weighted, and distribution analysis all at 100% success rate across 36 total requests. |
| **Redis Caching** | PASS | 12.8x speedup on cache hits (132ms cached vs 1.7s uncached). 80% hit rate on repeated queries. |
| **Semantic Caching** | PASS | 67% cache hit rate on paraphrased queries vs 0% for exact-match. Unrelated queries correctly rejected (no false positives). |
| **Guardrails** | PASS | 4/4 input tests correct (PII email/phone/SSN blocked, safe prompt passes). Output guardrails functional (JSON schema, code detection, word count). |

## Cluster Deployment State

- **Helm release**: portkey-gateway (revision 4)
- **Gateway**: 1+ replicas running (HPA active, min 1 / max 10)
- **Redis**: portkey-gateway-redis-master running (port 6379)
- **Ollama**: portkey-gateway-ollama running (port 11434, model: llama3)
- **vLLM Model**: llama-32-1b-fp8-metrics (port 8080, image: registry.redhat.io/rhoai/odh-vllm-cuda-rhel9)
- **K8s resources**: PDB, HPA deployed
- **NetworkPolicy**: Disabled (see Known Issues)

## Known Issues

### 1. NetworkPolicy DNS Resolution Failure

**Problem**: When NetworkPolicy is enabled, DNS resolution from gateway pods fails completely (EAI_AGAIN). OpenShift's CoreDNS runs as a ClusterIP service (172.30.0.10), which falls within the 172.16.0.0/12 private range. Standard `namespaceSelector` or even unrestricted port-only egress rules don't reliably cover ClusterIP-based DNS traffic in this environment.

**Current state**: NetworkPolicy is disabled (`networkPolicy.enabled: false`) to allow testing. The template is complete and ready for environments where DNS egress works correctly.

**Workaround options**:
- Keep disabled in non-production environments
- Use Calico or OVN-Kubernetes-specific DNS policies
- Add explicit CIDR-based egress rules for CoreDNS ClusterIP

### 2. Portkey Gateway OSS Lacks Prometheus Metrics

**Problem**: The open-source Portkey gateway Docker image (v1.15.x) does not include Prometheus metrics support. There is no `/metrics` endpoint, no `prom-client` dependency, and no `ENABLE_PROMETHEUS` environment variable in the bundled application code. This is an **Enterprise-only** feature.

**Impact**: All observability templates (ServiceMonitor, Grafana dashboard, PrometheusRule) and the observability demo have been removed from this POC since they cannot function with the OSS gateway.

**Potential resolution**: Portkey Gateway 2.0 is in pre-release and may merge some Enterprise features into the OSS version, but no stable release is available yet.

### 3. Portkey Gateway Rejects FQDN Custom Hosts

**Problem**: The Portkey gateway rejects fully-qualified domain names (`.svc.cluster.local`) in the `custom_host` field with "Invalid custom host" error.

**Workaround**: Use short Kubernetes service names (e.g., `http://llama-32-1b-fp8-metrics:8080/v1` instead of `http://llama-32-1b-fp8-metrics.your-namespace.svc.cluster.local:8080/v1`). This works when the gateway and target services are in the same namespace.

### 4. Portkey SDK Requires /v1 in base_url

**Problem**: The Portkey Python SDK appends `/chat/completions` directly to `base_url`. If `base_url` doesn't include `/v1`, requests get 404 errors.

**Resolution**: Always use `GATEWAY_API_URL` (includes `/v1`) rather than `GATEWAY_URL` for SDK calls.

### 5. Guardrails Config Format (Corrected)

**Problem**: Portkey guardrails use a non-obvious config format. Check IDs must be camelCase (e.g., `regexMatch` not `regex_match`). Each guardrail object has reserved keys (`deny`, `async`, `on_fail`, `on_success`, `id`) and every other key is treated as a check ID. `deny: true` is required to block requests (HTTP 446).

**Additional nuance**: For `regexMatch`, the check passes when the regex matches. To block content containing PII (where you want to deny when the regex matches), set `"not": true` to invert the check. Also, `wordCount` and `characterCount` do **not** work as input guardrails (`beforeRequestHooks`) -- they only evaluate response content in output guardrails.

## Portkey vs LiteLLM - Key Findings

### Portkey Advantages

1. **Built-in guardrails**: ~15 deterministic checks (regex, schema, word count, code detection) available in OSS gateway with no additional infrastructure. LiteLLM requires deploying LlamaGuard (GPU-backed model) for comparable safety checks.
2. **Lighter deployment**: Single container + optional Redis. No PostgreSQL requirement for basic operations.
3. **Wider provider support**: 250+ providers vs 100+.
4. **Semantic caching concept**: Enterprise version includes built-in semantic caching. OSS can implement custom approach (demonstrated in this POC).

### LiteLLM Advantages

1. **Budget enforcement**: Granular per-key/team/org budgets with RPM/TPM limits. Mature PostgreSQL-backed state management.
2. **Admin dashboard**: Built-in web UI in the OSS version (not SaaS-only like Portkey).
3. **Observability ecosystem**: Native integrations with Langfuse, Arize Phoenix, Langsmith, OpenTelemetry.
4. **Team management**: Full RBAC, self-service key creation, multi-team support.
5. **Cost attribution**: Multi-level spend tracking at key/user/team/org granularity.

### Critical Caveat: OSS vs Enterprise

Many of Portkey's headline features are **SaaS/Enterprise-only**:
- 60+ built-in guardrails (OSS has ~15 deterministic checks)
- Semantic caching (OSS has exact-match only)
- Prompt Management Studio (not available in OSS)
- Admin dashboard
- Pre-built observability dashboards

The OSS gateway is best characterized as a **lightweight routing proxy** with basic guardrails and caching. The Enterprise/SaaS version adds the developer experience and governance features that differentiate it from LiteLLM.
