#!/usr/bin/env python3
"""
Portkey AI Gateway - Redis Caching Demo

This demo demonstrates REAL caching using Redis deployed with the Portkey gateway.
Since the open-source Portkey gateway doesn't support per-request caching,
we implement application-level caching using Redis directly.

Usage:
    python redis_caching_demo.py [--provider ollama|llama-fp8]

Environment Variables:
    PORTKEY_GATEWAY_URL - The Portkey gateway URL (required)
    REDIS_HOST - Redis host (default: portkey-gateway-redis-master)
    REDIS_PORT - Redis port (default: 6379)
    REDIS_PASSWORD - Redis password (required)
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import redis

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent))

from portkey_ai import Portkey
from tabulate import tabulate

from config import (
    CACHE_MAX_AGE,
    GATEWAY_API_URL,
    get_provider_config,
    print_config,
)


class RedisCache:
    """Redis-based LLM response cache."""

    def __init__(self, host: str, port: int, password: str, default_ttl: int = 300):
        """
        Initialize Redis cache connection.

        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            default_ttl: Default cache TTL in seconds
        """
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        self.default_ttl = default_ttl

        # Test connection
        try:
            self.client.ping()
            print(f"✓ Connected to Redis at {host}:{port}")
        except redis.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def get_cache_key(self, provider: str, model: str, messages: list, **kwargs) -> str:
        """
        Generate a cache key from request parameters.

        Args:
            provider: LLM provider
            model: Model name
            messages: Chat messages
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            SHA256 hash as cache key
        """
        # Create a stable representation of the request
        key_data = {
            "provider": provider,
            "model": model,
            "messages": messages,
            "params": {k: v for k, v in sorted(kwargs.items())}
        }
        # Sort keys to ensure consistent hashing
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()
        return f"llm_cache:{key_hash}"

    def get(self, cache_key: str) -> Optional[dict]:
        """Get cached response."""
        try:
            cached = self.client.get(cache_key)
            if cached:
                return json.loads(cached)
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"  Warning: Cache read error: {e}")
        return None

    def set(self, cache_key: str, response: dict, ttl: Optional[int] = None):
        """Set cached response with TTL."""
        try:
            ttl = ttl or self.default_ttl
            self.client.setex(cache_key, ttl, json.dumps(response))
        except redis.RedisError as e:
            print(f"  Warning: Cache write error: {e}")

    def clear(self, pattern: str = "llm_cache:*"):
        """Clear cache entries matching pattern."""
        cursor = 0
        count = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern, count=100)
            if keys:
                self.client.delete(*keys)
                count += len(keys)
            if cursor == 0:
                break
        return count


def create_portkey_client(provider_config: dict) -> Portkey:
    """Create a Portkey client without caching config (since it's not supported)."""
    client = Portkey(
        base_url=GATEWAY_API_URL,
        api_key="not-needed-for-self-hosted",
        provider=provider_config["provider"],
        custom_host=provider_config["custom_host"],
    )
    return client


def make_cached_chat_request(
    cache: RedisCache,
    provider_config: dict,
    message: str,
    use_cache: bool = True,
) -> tuple[str, float, bool]:
    """
    Make a chat completion request with Redis caching.

    Args:
        cache: RedisCache instance
        provider_config: Provider configuration
        message: The user message to send
        use_cache: Whether to use caching

    Returns:
        Tuple of (response_content, elapsed_time_seconds, cache_hit)
    """
    messages = [{"role": "user", "content": message}]
    params = {"max_tokens": 100}

    # Generate cache key
    cache_key = cache.get_cache_key(
        provider=provider_config["provider"],
        model=provider_config["model"],
        messages=messages,
        **params
    )

    # Try to get from cache
    cache_hit = False
    if use_cache:
        start_time = time.time()
        cached_response = cache.get(cache_key)
        if cached_response:
            elapsed_time = time.time() - start_time
            content = cached_response["choices"][0]["message"]["content"].strip()
            return content, elapsed_time, True

    # Cache miss - make the API call
    client = create_portkey_client(provider_config)
    start_time = time.time()
    response = client.chat.completions.create(
        model=provider_config["model"],
        messages=messages,
        **params
    )
    elapsed_time = time.time() - start_time

    # Extract response content
    content = response.choices[0].message.content.strip()

    # Store in cache
    if use_cache:
        response_dict = response.model_dump()
        cache.set(cache_key, response_dict)

    return content, elapsed_time, False


def run_simple_cache_test(cache: RedisCache, provider_config: dict) -> dict:
    """
    Test simple (exact match) caching with Redis.

    Makes the same request twice and measures the time difference.
    """
    print("\n" + "=" * 60)
    print("TEST 1: Simple Cache (Exact Match) - Redis Implementation")
    print("=" * 60)

    test_message = "What is the capital of France? Answer in one word."

    print("\nSending identical request twice...")
    print(f"Message: '{test_message}'")

    # First request (cache miss expected)
    print("\n[Request 1] Sending first request (cache MISS expected)...")
    answer1, time1, hit1 = make_cached_chat_request(
        cache, provider_config, test_message, use_cache=True
    )
    cache1_status = "HIT" if hit1 else "MISS"
    print(f"  Response: {answer1[:80]}...")
    print(f"  Time: {time1:.3f}s | Cache: {cache1_status}")

    # Second request (cache hit expected)
    print("\n[Request 2] Sending identical request (cache HIT expected)...")
    answer2, time2, hit2 = make_cached_chat_request(
        cache, provider_config, test_message, use_cache=True
    )
    cache2_status = "HIT" if hit2 else "MISS"
    speedup = time1 / time2 if time2 > 0 else float("inf")
    print(f"  Response: {answer2[:80]}...")
    print(f"  Time: {time2:.3f}s | Cache: {cache2_status}")

    if hit2:
        print(f"\n  ✓ Cache HIT! Speedup: {speedup:.1f}x faster!")
        print(f"  Saved {time1 - time2:.3f}s by using cached response")
    else:
        print(f"\n  ✗ Cache MISS (unexpected)")

    return {
        "test": "Simple Cache (Redis)",
        "first_time": time1,
        "second_time": time2,
        "first_cache": cache1_status,
        "second_cache": cache2_status,
        "speedup": speedup,
    }


def run_no_cache_baseline(cache: RedisCache, provider_config: dict) -> dict:
    """
    Run a baseline test without caching for comparison.
    """
    print("\n" + "=" * 60)
    print("BASELINE: No Cache (Two Different Requests)")
    print("=" * 60)

    message1 = "What color is the sky on a clear day?"
    message2 = "How many legs does a spider have?"

    print("\nSending two different requests without caching...")

    # First request
    print(f"\n[Request 1] '{message1}'")
    answer1, time1, _ = make_cached_chat_request(
        cache, provider_config, message1, use_cache=False
    )
    print(f"  Response: {answer1[:80]}...")
    print(f"  Time: {time1:.3f}s")

    # Second request
    print(f"\n[Request 2] '{message2}'")
    answer2, time2, _ = make_cached_chat_request(
        cache, provider_config, message2, use_cache=False
    )
    print(f"  Response: {answer2[:80]}...")
    print(f"  Time: {time2:.3f}s")

    return {
        "test": "No Cache (Baseline)",
        "first_time": time1,
        "second_time": time2,
        "first_cache": "N/A",
        "second_cache": "N/A",
        "speedup": 1.0,
    }


def run_cache_persistence_test(cache: RedisCache, provider_config: dict) -> dict:
    """
    Test cache persistence across multiple identical requests.
    """
    print("\n" + "=" * 60)
    print("TEST 2: Cache Persistence (5 Identical Requests)")
    print("=" * 60)

    test_message = "What is 2+2? Answer in one word."
    num_requests = 5

    print(f"\nSending the same request {num_requests} times...")
    print(f"Message: '{test_message}'")

    times = []
    hits = []

    for i in range(num_requests):
        print(f"\n[Request {i+1}]")
        answer, elapsed, hit = make_cached_chat_request(
            cache, provider_config, test_message, use_cache=True
        )
        times.append(elapsed)
        hits.append(hit)
        cache_status = "HIT" if hit else "MISS"
        print(f"  Response: {answer[:80]}...")
        print(f"  Time: {elapsed:.3f}s | Cache: {cache_status}")

    # Calculate statistics
    first_time = times[0]
    avg_cached_time = sum(times[1:]) / len(times[1:]) if len(times) > 1 else 0
    speedup = first_time / avg_cached_time if avg_cached_time > 0 else 0
    hit_rate = sum(hits) / len(hits) * 100

    print(f"\n  Statistics:")
    print(f"  - First request (MISS): {first_time:.3f}s")
    print(f"  - Avg cached requests: {avg_cached_time:.3f}s")
    print(f"  - Cache hit rate: {hit_rate:.0f}%")
    print(f"  - Average speedup: {speedup:.1f}x")

    return {
        "test": "Cache Persistence",
        "first_time": first_time,
        "second_time": avg_cached_time,
        "first_cache": "MISS",
        "second_cache": f"HIT ({hit_rate:.0f}%)",
        "speedup": speedup,
    }


def print_results_table(results: list[dict]):
    """Print a formatted results table."""
    print("\n" + "=" * 60)
    print("REDIS CACHING DEMO RESULTS SUMMARY")
    print("=" * 60)

    table_data = []
    for r in results:
        table_data.append([
            r["test"],
            f"{r['first_time']:.3f}s",
            r["first_cache"],
            f"{r['second_time']:.3f}s",
            r["second_cache"],
            f"{r['speedup']:.1f}x",
        ])

    headers = ["Test", "1st Request", "1st Cache", "2nd Request", "2nd Cache", "Speedup"]
    print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))

    # Summary
    print("\n KEY TAKEAWAYS:")
    for r in results:
        if r["speedup"] > 1.5:
            print(f"  ✓ {r['test']}: {r['speedup']:.1f}x faster with Redis caching!")
        else:
            print(f"  - {r['test']}: Baseline (no caching)")


def main():
    parser = argparse.ArgumentParser(
        description="Portkey AI Gateway - Redis Caching Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Use Ollama (default)
    python redis_caching_demo.py

    # Use LLaMA FP8
    python redis_caching_demo.py --provider llama-fp8

    # Clear cache before running
    python redis_caching_demo.py --clear-cache

Environment Variables:
    REDIS_HOST - Redis host (default: portkey-gateway-redis-master)
    REDIS_PORT - Redis port (default: 6379)
    REDIS_PASSWORD - Redis password (required)
        """
    )
    parser.add_argument(
        "--provider",
        choices=["ollama", "llama-fp8"],
        default="ollama",
        help="LLM provider to use (default: ollama)"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear cache before running tests"
    )
    args = parser.parse_args()

    # Print configuration
    print_config()

    provider_config = get_provider_config(args.provider)
    print(f"\nUsing provider: {args.provider}")
    print(f"Model: {provider_config['model']}")
    print(f"Custom host: {provider_config['custom_host']}")

    # Redis configuration
    # Default to in-cluster service name (works from within the cluster)
    # For local development, use port-forward: kubectl port-forward svc/portkey-gateway-redis-master 6379:6379
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", "6379"))
    redis_password = os.environ.get("REDIS_PASSWORD")

    if not redis_password:
        print("\n ERROR: REDIS_PASSWORD environment variable is required")
        print("Get it from the Kubernetes secret:")
        print("  oc get secret portkey-gateway-redis -o jsonpath='{.data.redis-password}' | base64 -d")
        sys.exit(1)

    print(f"\nRedis Configuration:")
    print(f"  Host: {redis_host}")
    print(f"  Port: {redis_port}")
    print(f"  Password: {'*' * len(redis_password)}")

    # Initialize Redis cache
    try:
        cache = RedisCache(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            default_ttl=CACHE_MAX_AGE
        )
    except ConnectionError as e:
        print(f"\n ERROR: {e}")
        sys.exit(1)

    # Clear cache if requested
    if args.clear_cache:
        print("\nClearing cache...")
        count = cache.clear()
        print(f"  Cleared {count} cache entries")

    results = []

    try:
        # Run baseline test
        results.append(run_no_cache_baseline(cache, provider_config))

        # Run simple cache test
        results.append(run_simple_cache_test(cache, provider_config))

        # Run persistence test
        results.append(run_cache_persistence_test(cache, provider_config))

        # Print summary table
        print_results_table(results)

        print("\n✓ Demo completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
