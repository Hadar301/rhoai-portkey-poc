# Troubleshooting Guide

This guide consolidates common issues and solutions across all components of the Portkey AI Gateway deployment.

## Quick Reference

| Issue | Component | Severity | Solution Link |
|-------|-----------|----------|---------------|
| DNS resolution failure with NetworkPolicy | Gateway | High | [NetworkPolicy DNS](#networkpolicy-dns-resolution-failure) |
| FQDN rejection | Gateway/RHOAI | High | [FQDN Issues](#fqdn-custom-host-rejection) |
| Connection refused | RHOAI | Medium | [Connection Issues](#connection-refused-rhoai) |
| Cache misses | Redis | Medium | [Caching Issues](#redis-caching-issues) |
| Guardrails not triggering | Guardrails | Medium | [Guardrails Config](#guardrails-configuration-issues) |
| No metrics endpoint | Observability | Low | [Metrics](#prometheus-metrics-unavailable) |

## Infrastructure Issues

### NetworkPolicy DNS Resolution Failure

**Problem**: Gateway pods fail DNS resolution when NetworkPolicy is enabled.

**Symptoms**: 
- `EAI_AGAIN` DNS errors in gateway logs
- All external requests fail
- Ollama/RHOAI connectivity broken

**Root Cause**: OpenShift CoreDNS runs as ClusterIP service (172.30.0.10), which standard NetworkPolicy egress rules don't reliably cover.

**Solutions**:
```bash
# Option 1: Disable NetworkPolicy (recommended for testing)
helm upgrade portkey-gateway ./helm --set networkPolicy.enabled=false

# Option 2: Add explicit DNS egress rule
# Edit templates/networkpolicy.yaml to include:
# - to:
#   - namespaceSelector:
#       matchLabels:
#         name: openshift-dns
#   ports:
#   - protocol: UDP
#     port: 53

# Option 3: Use host-network pods (not recommended)
```

**Status**: Known limitation. NetworkPolicy template is complete but disabled by default.

### FQDN Custom Host Rejection

**Problem**: Portkey gateway rejects fully-qualified domain names (FQDNs) ending in `.svc.cluster.local`.

**Symptoms**:
- "Invalid custom host" errors in logs
- RHOAI model connectivity fails in cross-namespace deployments
- External providers work fine

**Solutions**:
```bash
# ✅ Correct (short service name)
export RHOAI_VLLM_PRIMARY_HOST="http://llama-32-1b-fp8-metrics:8080/v1"

# ❌ Incorrect (FQDN - rejected)
export RHOAI_VLLM_PRIMARY_HOST="http://llama-32-1b-fp8-metrics.rhoai-models.svc.cluster.local:8080/v1"
```

**Workarounds**:
1. **Same-namespace deployment**: Deploy gateway and models in same namespace
2. **Environment variables**: Use short names in `demos/config.py`
3. **NetworkPolicy egress**: Configure cross-namespace access (if NetworkPolicy enabled)

**Status**: Gateway limitation, affects cross-namespace RHOAI integration.

### Prometheus Metrics Unavailable

**Problem**: OSS Portkey gateway has no `/metrics` endpoint.

**Symptoms**:
- 404 errors on `http://gateway:8080/metrics`
- ServiceMonitor shows no targets
- Grafana dashboards show no data

**Resolution**: This is an **Enterprise-only feature**. The OSS gateway v1.15.x does not include Prometheus support.

**Alternatives**:
- Use application-level metrics from demo scripts
- Monitor via OpenShift native metrics (pod CPU/memory)
- Consider Portkey Enterprise for full observability

## RHOAI Integration Issues

### Connection Refused (RHOAI)

**Problem**: Gateway cannot reach RHOAI KServe models.

**Diagnosis Steps**:
```bash
# 1. Check InferenceService status
oc get inferenceservice -n rhoai-models

# 2. Verify predictor pod is running  
oc get pods -n rhoai-models

# 3. Test direct connectivity from gateway pod
oc exec -n portkey-gateway deploy/portkey-gateway -- \
  curl -s http://llama-32-1b-fp8-metrics:8080/v1/models

# 4. Check service endpoints
oc get endpoints -n rhoai-models
```

**Common Causes**:
- InferenceService not ready (check `.status.conditions`)
- Predictor pod crashlooping (check logs)
- Service name mismatch (verify with `oc get svc`)
- Cross-namespace NetworkPolicy blocking traffic

**Solutions**:
```bash
# Verify model endpoint responds
curl -X POST "http://model-service:8080/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama-32-1b-fp8", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'
```

### Model Not Found (RHOAI)

**Problem**: Gateway connects but returns "model not found" errors.

**Diagnosis**:
```bash
# Check available models
curl http://model-endpoint:8080/v1/models | jq '.data[].id'
```

**Solutions**:
- Update model name in `demos/config.py` to match vLLM output
- Common pattern: HuggingFace model ID (e.g., `meta-llama/Llama-3.2-1B`)
- Verify model name consistency across InferenceService and config

## Caching Issues

### Redis Caching Issues

**Problem**: Cache misses or Redis connection failures.

**Diagnosis**:
```bash
# Check Redis pod status
oc get pods -l app.kubernetes.io/name=redis

# Test Redis connectivity
oc exec -it deploy/portkey-gateway -- redis-cli -h portkey-gateway-redis-master ping

# Check Redis password
export REDIS_PASSWORD=$(oc get secret portkey-gateway-redis -o jsonpath='{.data.redis-password}' | base64 -d)
echo $REDIS_PASSWORD
```

**Common Issues**:
- Incorrect Redis password in environment variables
- Redis master pod not running
- Network policy blocking Redis traffic (port 6379)
- Cache keys not matching (SHA256 hash differences)

**Solutions**:
```bash
# Clear Redis cache
oc exec -it deploy/portkey-gateway-redis-master -- redis-cli FLUSHALL

# Verify cache key generation
# Keys should be SHA256 hash of: prompt + model + max_tokens + other parameters
```

### Semantic Caching Issues

**Problem**: Low cache hit rates or embedding generation failures.

**Common Causes**:
- Ollama `/v1/embeddings` endpoint not available
- Similarity threshold too high (default 0.90)
- Embedding model mismatch between cache and lookup

**Solutions**:
```bash
# Test embedding endpoint
curl -X POST "http://ollama-endpoint:11434/v1/embeddings" \
  -H "Content-Type: application/json" \
  -d '{"input": "test query", "model": "llama3"}'

# Adjust similarity threshold
uv run python semantic_caching_demo.py --threshold 0.85

# Clear embedding cache
redis-cli DEL semantic_cache:*
```

## Application Issues

### Guardrails Configuration Issues

**Problem**: Guardrails not triggering or incorrectly configured.

**Common Mistakes**:
```python
# ❌ Wrong - snake_case check ID
{"deny": True, "regex_match": {"rule": "email_pattern"}}

# ✅ Correct - camelCase check ID  
{"deny": True, "regexMatch": {"rule": r"\b[\w.-]+@[\w.-]+\.\w+\b"}}
```

**Configuration Validation**:
```bash
# Test guardrails with known triggers
uv run python guardrails_demo.py --scenario input

# Check for reserved keys conflict
# Reserved: deny, async, on_fail, on_success, id, type
# Everything else = check ID
```

**Input vs Output Guardrails**:
- `wordCount`, `characterCount` **only work as output guardrails**
- Input guardrails: `regexMatch`, `contains`, `jsonSchema`
- Set `"deny": true` to block requests (HTTP 446)

### Environment Variables Issues

**Problem**: Demos fail with configuration errors.

**Required Variables**:
```bash
# Gateway access
export PORTKEY_GATEWAY_URL="https://$(oc get route portkey-gateway -o jsonpath='{.spec.host}')/v1"

# Redis access (for caching demos)
export REDIS_PASSWORD=$(oc get secret portkey-gateway-redis -o jsonpath='{.data.redis-password}' | base64 -d)

# RHOAI access (if using RHOAI models)  
export RHOAI_VLLM_PRIMARY_HOST="http://model-name:8080/v1"
export RHOAI_VLLM_PRIMARY_MODEL="model-id"
```

**Validation**:
```bash
# Test gateway connectivity
curl -X POST "$PORTKEY_GATEWAY_URL/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3", "messages": [{"role": "user", "content": "test"}], "max_tokens": 10}'

# Test Redis connectivity  
redis-cli -h portkey-gateway-redis-master -a "$REDIS_PASSWORD" ping
```

## Recovery Procedures

### Full Stack Reset
```bash
# 1. Uninstall everything
./uninstall.sh your-namespace --delete-namespace

# 2. Clean reinstall
./install.sh your-namespace

# 3. Verify basic connectivity
oc get pods -n your-namespace
oc get routes -n your-namespace

# 4. Test with simple demo
uv run python demos/guardrails/guardrails_demo.py --scenario basic --provider ollama
```

### Gateway Pod Reset
```bash
# Restart gateway deployment
oc rollout restart deployment/portkey-gateway

# Check new pod logs
oc logs -f deployment/portkey-gateway

# Verify route accessibility
curl -I "https://$(oc get route portkey-gateway -o jsonpath='{.spec.host}')"
```

### Redis Cache Reset
```bash
# Clear all cached data
oc exec -it deploy/portkey-gateway-redis-master -- redis-cli FLUSHALL

# Restart Redis for full reset
oc rollout restart statefulset/portkey-gateway-redis-master
```

## Getting Help

### Logs Collection
```bash
# Gateway logs
oc logs deployment/portkey-gateway --tail=100

# Redis logs
oc logs statefulset/portkey-gateway-redis-master

# Ollama logs (if deployed)
oc logs deployment/portkey-gateway-ollama
```

### Common Debug Commands
```bash
# Check all pod status
oc get pods -o wide

# Test internal DNS resolution
oc exec deployment/portkey-gateway -- nslookup ollama-service

# Verify port-forwarding works
oc port-forward svc/portkey-gateway 8080:8080
curl http://localhost:8080/health
```

### External Resources
- [Portkey Documentation](https://portkey.ai/docs)
- [OpenShift DNS Troubleshooting](https://docs.openshift.com/container-platform/4.14/networking/dns-operator.html)
- [Redis Troubleshooting](https://redis.io/docs/management/debugging/)
- [Known Issues in summary.md](summary.md#known-issues) - Complete list with technical details