# Portkey vs LiteLLM: Comparison Matrix

## Platform Overview

**Portkey**: AI operations platform focused on developer experience and governance. Emphasizes prompt management, semantic caching, built-in guardrails, and request-level tracing.

**LiteLLM**: Comprehensive LLM operations platform focused on infrastructure-level operations. Emphasizes budget enforcement, team management, cost attribution, and multi-provider routing.

**Key Insight**: These platforms have **complementary strengths** rather than being direct replacements for each other.

## Feature Comparison

| Feature | Portkey OSS | Portkey Enterprise | LiteLLM OSS | Notes |
|---------|-------------|-------------------|-------------|-------|
| **Routing & Reliability** | | | | |
| Multi-provider routing | 250+ providers | 250+ providers | 100+ providers | Portkey has wider coverage |
| Automatic failover | Built-in | Built-in | Built-in | Feature parity |
| Load balancing | Weighted | Weighted | Weighted | Feature parity |
| Retries w/ backoff | Built-in | Built-in | Built-in | Feature parity |
| Timeout controls | Built-in | Built-in | Built-in | Feature parity |
| | | | | |
| **Caching** | | | | |
| Simple (exact-match) | Redis | Redis | Redis | Feature parity |
| Semantic caching | Custom impl | Built-in | No | Portkey advantage |
| | | | | |
| **Safety & Guardrails** | | | | |
| Built-in guardrails | ~15 deterministic checks | 60+ checks | Content filters | Portkey advantage |
| PII detection | Regex-based | Regex + LLM | Via LlamaGuard | Portkey: no GPU needed |
| JSON schema validation | Built-in | Built-in | No | Portkey advantage |
| Prompt injection detection | LLM-based | LLM-based | Via LlamaGuard | Different approaches |
| Custom guardrails | Webhooks | Webhooks + partners | Custom code | Portkey more flexible |
| | | | | |
| **Operations** | | | | |
| Budget management | Basic | Advanced | Full (key/team/org) | LiteLLM advantage |
| Team management | No | Yes | Full RBAC | LiteLLM advantage |
| Admin dashboard | No | Yes | Yes (built-in) | LiteLLM has OSS UI |
| Virtual API keys | No | Yes | Yes (self-service) | LiteLLM advantage |
| Rate limiting (RPM/TPM) | No | Yes | Yes | LiteLLM advantage |
| | | | | |
| **Observability** | | | | |
| Prometheus metrics | Not available | 15+ metrics | Basic | Enterprise-only for Portkey |
| Grafana dashboards | Not available | Pre-built | Manual | Enterprise-only for Portkey |
| External integrations | None | Full suite | Langfuse/Phoenix/OTEL | LiteLLM richer ecosystem |
| Cost tracking | Per-request metric | Advanced | Multi-level (PostgreSQL) | LiteLLM more granular |
| Token tracking | Input/output counts | Detailed | Via spend logs | Feature parity |
| Request tracing | Basic | Detailed | Via integrations | Different approaches |
| | | | | |
| **Developer Experience** | | | | |
| Prompt management | Not available | Full Studio UI | No | Enterprise-only |
| Prompt versioning | Not available | Built-in | No | Enterprise-only |
| A/B testing | Not available | Built-in | No | Enterprise-only |
| SDK support | Python, Node.js | Python, Node.js | Python, Node.js | Feature parity |
| OpenAI compatibility | Drop-in | Drop-in | Drop-in | Feature parity |
| | | | | |
| **Deployment** | | | | |
| Container footprint | Single container | Single container | Container + PostgreSQL | Portkey lighter |
| Database requirement | Redis (optional) | Redis | PostgreSQL (required) | Portkey simpler |
| OpenShift compatible | Yes | Yes | Yes | Feature parity |
| Helm chart | Yes (this repo) | Yes | Yes | Feature parity |
| Edge deployment | Cloudflare Workers | Cloudflare Workers | No | Portkey advantage |
| | | | | |
| **Compliance** | | | | |
| SOC-2 | No | Yes | Yes | Enterprise feature |
| ISO 27001 | No | Yes | Yes | Enterprise feature |
| HIPAA | No | Yes | Yes | Enterprise feature |
| GDPR | No | Yes | Yes | Enterprise feature |

## When to Choose Portkey

- **Built-in guardrails** are a priority (PII, prompt injection, schema validation)
- **Semantic caching** is needed to improve cache hit rates
- **Lightweight deployment** is preferred (no PostgreSQL dependency)
- **Developer experience** matters (request tracing, SDK ergonomics)
- **Wider provider support** needed (250+ vs 100+)

## When to Choose LiteLLM

- **Budget enforcement** at team/org level is critical
- **Admin dashboard** for non-technical stakeholders is needed (OSS, not SaaS-only)
- **Observability ecosystem** integration required (Langfuse, Phoenix, Langsmith)
- **Cost attribution** at multiple levels (key/user/team/org) is needed
- **LlamaStack integration** for agents/RAG workflows is a requirement
