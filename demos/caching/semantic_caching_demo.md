# Semantic Caching Demo

## Overview

This demo compares **simple (exact-match) caching** with **semantic caching**. While Portkey's OSS gateway supports simple Redis caching, this demo implements a semantic cache layer using real embeddings from Ollama (via the Portkey gateway) to demonstrate the concept and benefits.

## Why Semantic Caching?

Real-world users ask the same question in different ways:

| Query | Simple Cache | Semantic Cache |
|-------|-------------|----------------|
| "What is the capital of France?" | HIT (original) | HIT (original) |
| "Which city serves as the capital of France?" | MISS | HIT |
| "Tell me the capital city of France" | MISS | HIT |
| "How many planets are in the solar system?" | MISS | MISS |

Semantic caching uses real embedding vectors to measure similarity between queries, catching paraphrases that exact-match caching misses entirely.

## Implementation

### Simple Cache (Baseline)
- Uses SHA256 hash of the exact query string
- Only matches byte-identical queries
- Fast but low hit rate for real traffic

### Semantic Cache (This Demo)
- Uses Ollama's `/v1/embeddings` endpoint via the Portkey gateway for real embedding vectors
- Compares new queries against cached embeddings using cosine similarity
- Returns cached response when similarity exceeds threshold (default: 0.90)
- Handles real paraphrases with different wording and synonyms
- No extra ML dependencies — embeddings come from the already-deployed Ollama instance

### Portkey Enterprise
- Built-in semantic caching with no custom code needed
- Configured via the Portkey config
- Supports configurable similarity thresholds
- Integrated with the caching pipeline

## Running the Demo

```bash
# Set Redis credentials
export REDIS_PASSWORD=$(oc get secret portkey-gateway-redis -o jsonpath='{.data.redis-password}' | base64 -d)

# Run demo
uv run python demos/caching/semantic_caching_demo.py

# Adjust similarity threshold
uv run python demos/caching/semantic_caching_demo.py --threshold 0.85

# Use a different embedding model
uv run python demos/caching/semantic_caching_demo.py --embedding-model llama3

# Use RHOAI model for chat (embeddings always use Ollama)
uv run python demos/caching/semantic_caching_demo.py --provider rhoai-primary
```

## Dependencies

```
redis       # For cache storage
portkey-ai  # For embedding requests via the Portkey gateway
```

## Architecture

```
Query → Portkey Gateway → Ollama → Embedding vector
                                         ↓
                                   Cosine similarity
                                   against cached embeddings
                                         ↓
                              HIT (above threshold) → Return cached response
                              MISS → Call LLM, cache response + embedding
```

Embeddings are always generated via Ollama (which supports the OpenAI-compatible `/v1/embeddings` endpoint). Chat completions can use any provider (Ollama, vLLM, RHOAI models).

## Cost Savings

- **Cache hit rate improvement**: Semantic caching catches paraphrased queries that exact-match misses entirely
- **Latency reduction**: Cache hits return in milliseconds vs 1-2s for LLM calls
- **Cost reduction**: Proportional to cache hit rate improvement
