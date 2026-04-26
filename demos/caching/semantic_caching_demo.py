#!/usr/bin/env python3
"""
Portkey AI Gateway - Semantic Caching Demo

Demonstrates semantic caching beyond simple exact-match caching.
While Portkey's OSS gateway supports simple caching via Redis,
this demo implements a semantic cache layer using real embeddings
from Ollama (via the Portkey gateway) to show the concept and benefits.

Semantic caching matches semantically similar queries (not just exact matches),
dramatically improving cache hit rates for real-world traffic where users
ask the same question in different ways.

Usage:
    uv run python demos/caching/semantic_caching_demo.py [--provider ollama|llama-fp8]

Environment Variables:
    PORTKEY_GATEWAY_URL - The Portkey gateway URL
    REDIS_HOST          - Redis host (default: localhost)
    REDIS_PORT          - Redis port (default: 6379)
    REDIS_PASSWORD      - Redis password (required)
"""

import argparse
import hashlib
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import redis
from portkey_ai import Portkey
from tabulate import tabulate

sys.path.insert(0, str(Path(__file__).parent.parent))


from config import (
    CACHE_MAX_AGE,
    GATEWAY_API_URL,
    OLLAMA_CONFIG,
    get_provider_config,
    print_config,
)

# =============================================================================
# Embedding Client
# =============================================================================


def get_embedding(text: str, embedding_client: Portkey, model: str) -> list[float]:
    """
    Get an embedding vector from Ollama via the Portkey gateway.

    Uses Ollama's OpenAI-compatible /v1/embeddings endpoint, routed
    through the Portkey gateway.
    """
    response = embedding_client.embeddings.create(
        input=text,
        model=model,
    )
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# =============================================================================
# Semantic Cache Implementation
# =============================================================================


class SemanticCache:
    """
    Semantic cache using real embeddings for similarity matching.

    Uses Ollama's embedding endpoint (via the Portkey gateway) to generate
    real embedding vectors for queries. When a new query is semantically
    similar to a cached query (above threshold), the cached response is
    returned instead of calling the LLM.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        embedding_client: Portkey,
        embedding_model: str,
        similarity_threshold: float = 0.90,
        default_ttl: int = 300,
    ):
        self.redis_client = redis_client
        self.embedding_client = embedding_client
        self.embedding_model = embedding_model
        self.threshold = similarity_threshold
        self.default_ttl = default_ttl
        self._cache_prefix = "semantic_cache:"

    def _get_embedding(self, text: str) -> list[float]:
        """Get embedding from Ollama via the Portkey gateway."""
        return get_embedding(text, self.embedding_client, self.embedding_model)

    def _get_all_cached_keys(self) -> list[str]:
        """Get all semantic cache keys from Redis."""
        keys = []
        cursor = 0
        while True:
            cursor, batch = self.redis_client.scan(
                cursor, match=f"{self._cache_prefix}*:meta", count=100
            )
            keys.extend(batch)
            if cursor == 0:
                break
        return keys

    def get(self, query: str) -> tuple[dict | None, float, str]:
        """
        Look up a semantically similar cached response.

        Returns:
            Tuple of (cached_response, similarity_score, matched_query)
        """
        query_embedding = self._get_embedding(query)

        best_match = None
        best_score = 0.0
        best_query = ""

        for meta_key in self._get_all_cached_keys():
            try:
                meta = self.redis_client.get(meta_key)
                if not meta:
                    continue
                meta = json.loads(meta)
                cached_embedding = meta["embedding"]
                similarity = cosine_similarity(query_embedding, cached_embedding)

                if similarity > best_score:
                    best_score = similarity
                    best_match = meta
                    best_query = meta.get("query", "")
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        if best_score >= self.threshold and best_match:
            response_key = best_match.get("response_key", "")
            cached = self.redis_client.get(response_key)
            if cached:
                return json.loads(cached), best_score, best_query

        return None, best_score, best_query

    def set(self, query: str, response: dict, ttl: int = None):
        """Cache a response with its embedding for semantic matching."""
        ttl = ttl or self.default_ttl
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

        embedding = self._get_embedding(query)
        meta_key = f"{self._cache_prefix}{query_hash}:meta"
        response_key = f"{self._cache_prefix}{query_hash}:response"

        meta = {
            "query": query,
            "embedding": embedding,
            "response_key": response_key,
            "timestamp": time.time(),
        }

        self.redis_client.setex(meta_key, ttl, json.dumps(meta))
        self.redis_client.setex(response_key, ttl, json.dumps(response))

    def clear(self) -> int:
        """Clear all semantic cache entries."""
        cursor = 0
        count = 0
        while True:
            cursor, keys = self.redis_client.scan(
                cursor, match=f"{self._cache_prefix}*", count=100
            )
            if keys:
                self.redis_client.delete(*keys)
                count += len(keys)
            if cursor == 0:
                break
        return count


# =============================================================================
# Simple (Exact Match) Cache for Comparison
# =============================================================================


class SimpleCache:
    """Simple exact-match cache for comparison with semantic cache."""

    def __init__(self, redis_client: redis.Redis, default_ttl: int = 300):
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self._prefix = "simple_cache:"

    def _get_key(self, query: str) -> str:
        return f"{self._prefix}{hashlib.sha256(query.encode()).hexdigest()}"

    def get(self, query: str) -> dict | None:
        cached = self.redis_client.get(self._get_key(query))
        return json.loads(cached) if cached else None

    def set(self, query: str, response: dict, ttl: int = None):
        self.redis_client.setex(
            self._get_key(query), ttl or self.default_ttl, json.dumps(response)
        )

    def clear(self) -> int:
        cursor = 0
        count = 0
        while True:
            cursor, keys = self.redis_client.scan(cursor, match=f"{self._prefix}*", count=100)
            if keys:
                self.redis_client.delete(*keys)
                count += len(keys)
            if cursor == 0:
                break
        return count


# =============================================================================
# Demo Execution
# =============================================================================

# Semantically similar query pairs for testing.
# These include real paraphrases with different wording and synonyms —
# the real embedding model handles semantic similarity properly.
SEMANTIC_TEST_PAIRS = [
    {
        "original": "What is the capital of France?",
        "similar": [
            "Which city serves as the capital of France?",
            "Tell me the capital city of France",
            "France's capital — what is it?",
        ],
        "unrelated": "How many planets are in the solar system?",
    },
    {
        "original": "How does photosynthesis work in plants?",
        "similar": [
            "Explain the process of photosynthesis in plants",
            "Can you describe how plants perform photosynthesis?",
            "What is the mechanism of photosynthesis?",
        ],
        "unrelated": "What is the tallest building in the world?",
    },
    {
        "original": "What are the benefits of machine learning?",
        "similar": [
            "Why is machine learning useful?",
            "What advantages does machine learning offer?",
            "List some benefits of using ML",
        ],
        "unrelated": "How do you make chocolate cake?",
    },
]


def make_llm_request(provider_config: dict, message: str) -> tuple[str, float]:
    """Make an LLM request and return (response_text, elapsed_seconds, response_dict)."""
    client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="not-needed",
        provider=provider_config["provider"],
        custom_host=provider_config["custom_host"],
    )

    start = time.time()
    response = client.chat.completions.create(
        model=provider_config["model"],
        messages=[{"role": "user", "content": message}],
        max_tokens=100,
    )
    elapsed = time.time() - start

    content = response.choices[0].message.content.strip() if response.choices else ""
    return content, elapsed, response.model_dump()


def run_semantic_vs_simple_demo(
    semantic_cache: SemanticCache,
    simple_cache: SimpleCache,
    provider_config: dict,
):
    """
    Compare semantic caching vs simple (exact-match) caching.

    Shows how semantic cache hits on paraphrased queries while simple cache misses.
    """
    print("\n" + "=" * 70)
    print("SEMANTIC CACHING vs SIMPLE CACHING COMPARISON")
    print("=" * 70)
    print()
    print("Simple cache: Only matches exact query strings (SHA256 hash)")
    print("Semantic cache: Matches semantically similar queries (Ollama embeddings)")
    print(f"Embedding model: {semantic_cache.embedding_model}")
    print(f"Similarity threshold: {semantic_cache.threshold}")
    print()

    # Clear both caches
    semantic_cache.clear()
    simple_cache.clear()

    all_results = []

    for test_set in SEMANTIC_TEST_PAIRS:
        original = test_set["original"]
        similar_queries = test_set["similar"]
        unrelated = test_set["unrelated"]

        print(f"\n{'─' * 70}")
        print(f'Original query: "{original}"')
        print(f"{'─' * 70}")

        # Step 1: Cache the original query
        print("\n  [1] Caching original query...")
        content, elapsed, response_dict = make_llm_request(provider_config, original)
        semantic_cache.set(original, response_dict)
        simple_cache.set(original, response_dict)
        print(f"      LLM response ({elapsed:.2f}s): {content[:60]}...")

        # Step 2: Test with similar queries
        for i, similar in enumerate(similar_queries, 1):
            print(f'\n  [{i + 1}] Testing: "{similar}"')

            # Simple cache lookup
            simple_start = time.time()
            simple_result = simple_cache.get(similar)
            simple_time = (time.time() - simple_start) * 1000
            simple_hit = simple_result is not None

            # Semantic cache lookup
            sem_start = time.time()
            sem_result, sem_score, _ = semantic_cache.get(similar)
            sem_time = (time.time() - sem_start) * 1000
            sem_hit = sem_result is not None

            print(
                f"      Simple cache:   {'HIT' if simple_hit else 'MISS':4s} ({simple_time:.1f}ms)"
            )
            print(
                f"      Semantic cache: {'HIT' if sem_hit else 'MISS':4s} ({sem_time:.1f}ms, similarity: {sem_score:.3f})"
            )

            all_results.append(
                {
                    "query": similar[:40],
                    "type": "Similar",
                    "simple": "HIT" if simple_hit else "MISS",
                    "semantic": "HIT" if sem_hit else "MISS",
                    "similarity": f"{sem_score:.3f}",
                    "simple_ms": f"{simple_time:.1f}",
                    "semantic_ms": f"{sem_time:.1f}",
                }
            )

        # Step 3: Test with unrelated query
        print(f'\n  [*] Unrelated: "{unrelated}"')
        sem_result, sem_score, _ = semantic_cache.get(unrelated)
        simple_result = simple_cache.get(unrelated)
        print(f"      Simple cache:   {'HIT' if simple_result else 'MISS':4s}")
        print(
            f"      Semantic cache: {'HIT' if sem_result else 'MISS':4s} (similarity: {sem_score:.3f})"
        )

        all_results.append(
            {
                "query": unrelated[:40],
                "type": "Unrelated",
                "simple": "HIT" if simple_result else "MISS",
                "semantic": "HIT" if sem_result else "MISS",
                "similarity": f"{sem_score:.3f}",
                "simple_ms": "-",
                "semantic_ms": "-",
            }
        )

    # Print summary table
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    table = [
        [r["query"], r["type"], r["simple"], r["semantic"], r["similarity"]] for r in all_results
    ]
    print(
        tabulate(
            table,
            headers=["Query", "Type", "Simple Cache", "Semantic Cache", "Similarity"],
            tablefmt="grid",
        )
    )

    # Calculate hit rates
    similar_results = [r for r in all_results if r["type"] == "Similar"]
    simple_hits = sum(1 for r in similar_results if r["simple"] == "HIT")
    semantic_hits = sum(1 for r in similar_results if r["semantic"] == "HIT")
    total = len(similar_results)

    print("\n  Cache Hit Rates (for similar/paraphrased queries):")
    print(f"    Simple (exact-match): {simple_hits}/{total} ({simple_hits / total * 100:.0f}%)")
    print(
        f"    Semantic (embedding):  {semantic_hits}/{total} ({semantic_hits / total * 100:.0f}%)"
    )
    print()

    if semantic_hits > simple_hits:
        improvement = ((semantic_hits - simple_hits) / max(total, 1)) * 100
        print(f"  Semantic cache provides {improvement:.0f}% more cache hits!")
        print("  This translates to fewer LLM calls, lower latency, and reduced costs.")
    print()
    print("  NOTE: Portkey Enterprise includes built-in semantic caching.")
    print("  This demo uses Ollama embeddings routed through the Portkey gateway.")


def main():
    parser = argparse.ArgumentParser(
        description="Portkey AI Gateway - Semantic Caching Demo",
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "llama-fp8", "rhoai-primary", "rhoai-secondary"],
        default="ollama",
        help="LLM provider for chat completions (default: ollama)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.90,
        help="Semantic similarity threshold (default: 0.90)",
    )
    parser.add_argument(
        "--embedding-model",
        default="llama3",
        help="Ollama model to use for embeddings (default: llama3)",
    )
    args = parser.parse_args()

    print_config()

    provider_config = get_provider_config(args.provider)
    print(f"\nChat provider: {args.provider} (model: {provider_config['model']})")
    print(f"Embedding provider: ollama (model: {args.embedding_model})")

    # Redis configuration
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_password = os.environ.get("REDIS_PASSWORD")

    if not redis_password:
        print("\nERROR: REDIS_PASSWORD environment variable is required")
        print("Get it from the Kubernetes secret:")
        print(
            "  oc get secret portkey-gateway-redis -o jsonpath='{.data.redis-password}' | base64 -d"
        )
        sys.exit(1)

    redis_client = redis.Redis(
        host=redis_host,
        port=redis_port,
        password=redis_password,
        decode_responses=True,
        socket_connect_timeout=5,
    )

    try:
        redis_client.ping()
        print(f"Connected to Redis at {redis_host}:{redis_port}")
    except redis.ConnectionError as e:
        print(f"\nERROR: Failed to connect to Redis: {e}")
        sys.exit(1)

    # Create embedding client — always uses Ollama via the Portkey gateway
    embedding_client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="not-needed",
        provider=OLLAMA_CONFIG["provider"],
        custom_host=OLLAMA_CONFIG["custom_host"],
    )

    # Verify embedding endpoint works
    print(f"Testing embedding endpoint (model: {args.embedding_model})...")
    try:
        test_emb = get_embedding("test", embedding_client, args.embedding_model)
        print(f"  Embedding dimension: {len(test_emb)}")
    except Exception as e:
        print(f"\nERROR: Failed to get embeddings from Ollama: {e}")
        print("Make sure Ollama is running and the model supports embeddings.")
        sys.exit(1)

    semantic_cache = SemanticCache(
        redis_client,
        embedding_client=embedding_client,
        embedding_model=args.embedding_model,
        similarity_threshold=args.threshold,
        default_ttl=CACHE_MAX_AGE,
    )
    simple_cache = SimpleCache(redis_client, default_ttl=CACHE_MAX_AGE)

    try:
        run_semantic_vs_simple_demo(semantic_cache, simple_cache, provider_config)
        print("\nSemantic caching demo completed.")
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
