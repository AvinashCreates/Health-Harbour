"""Measure health and an optional authenticated GET against a running API.

Use synthetic accounts and a non-production instance. This runner does not
seed data or create clinical records. For staged virtual-user ramping, use
the k6 runner in security/run-k6.sh.

Required setup:
    LOAD_TEST_URL=http://127.0.0.1:8000
    LOAD_TEST_TOKEN=<short-lived synthetic-user access token>  # optional
    LOAD_TEST_READ_PATH=/auth/me  # optional, must be authorized for the token
"""
import asyncio
import ipaddress
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

BASE_URL = os.getenv("LOAD_TEST_URL", "http://127.0.0.1:8000").rstrip("/")
AUTH_TOKEN = os.getenv("LOAD_TEST_TOKEN")
AUTH_PATH = os.getenv("LOAD_TEST_READ_PATH", "/auth/me")
CONCURRENCY_LEVELS = (1, 10, 50)
REQUESTS_PER_LEVEL = int(os.getenv("LOAD_TEST_REQUESTS", "100"))
OUTPUT_PATH = Path(os.getenv("LOAD_TEST_OUTPUT", "/tmp/healthharbor-loadtest.json"))


def validate_local_target(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("LOAD_TEST_URL must be an HTTP(S) loopback URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("LOAD_TEST_URL must not include credentials, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("LOAD_TEST_URL must be an origin without a path")

    hostname = parsed.hostname.lower()
    try:
        is_loopback = ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        is_loopback = hostname == "localhost"
    if not is_loopback:
        raise ValueError("Refusing non-loopback load-test target")
    return url.rstrip("/")


async def timed_get(client: httpx.AsyncClient, path: str, headers=None):
    started = time.perf_counter()
    try:
        response = await client.get(path, headers=headers)
        return (time.perf_counter() - started) * 1000, response.status_code
    except httpx.HTTPError:
        return (time.perf_counter() - started) * 1000, 0


async def run_phase(client, name, concurrency, total, call):
    semaphore = asyncio.Semaphore(concurrency)
    results = []

    async def worker(index):
        async with semaphore:
            results.append(await call(index))

    started = time.perf_counter()
    await asyncio.gather(*(worker(index) for index in range(total)))
    elapsed = time.perf_counter() - started
    latencies = sorted(duration for duration, _ in results)
    successes = sum(200 <= status < 300 for _, status in results)
    status_counts = {}
    for _, status in results:
        key = str(status) if status else "network_error"
        status_counts[key] = status_counts.get(key, 0) + 1

    def percentile(value):
        return round(latencies[min(len(latencies) - 1, int(value * len(latencies)))], 1)

    return {
        "phase": name,
        "concurrency": concurrency,
        "requests": len(results),
        "successes": successes,
        "error_rate": round((len(results) - successes) / len(results), 4),
        "throughput_rps": round(len(results) / elapsed, 2) if elapsed else 0,
        "p50_ms": percentile(0.50),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
        "status_counts": status_counts,
    }


async def main():
    if REQUESTS_PER_LEVEL < 1:
        raise ValueError("LOAD_TEST_REQUESTS must be a positive integer")
    if not AUTH_PATH.startswith("/") or AUTH_PATH.startswith("//"):
        raise ValueError("LOAD_TEST_READ_PATH must be an absolute API path")
    try:
        target_url = validate_local_target(BASE_URL)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"} if AUTH_TOKEN else None
    results = []
    limits = httpx.Limits(max_connections=max(CONCURRENCY_LEVELS) + 5)
    timeout = httpx.Timeout(30.0, connect=5.0)

    async with httpx.AsyncClient(
        base_url=target_url,
        limits=limits,
        timeout=timeout,
        follow_redirects=False,
    ) as client:
        try:
            response = await client.get("/health", timeout=5.0)
            response.raise_for_status()
            if response.json().get("status") != "healthy":
                raise RuntimeError("API health response did not report healthy")
        except (httpx.HTTPError, ValueError, RuntimeError) as error:
            print(f"API is not ready at {BASE_URL}: {error}", file=sys.stderr)
            return 1

        phases = [("health", "/health", None)]
        if headers:
            phases.append(("authenticated_read", AUTH_PATH, headers))
        else:
            print("LOAD_TEST_TOKEN is unset; authenticated-read results are skipped.")

        for concurrency in CONCURRENCY_LEVELS:
            print(f"\nConcurrency {concurrency}")
            for name, path, request_headers in phases:
                call = lambda _index, path=path, request_headers=request_headers: timed_get(
                    client, path, request_headers
                )
                result = await run_phase(
                    client, name, concurrency, REQUESTS_PER_LEVEL, call
                )
                results.append(result)
                print(
                    f"{name}: {result['successes']}/{result['requests']} successful, "
                    f"{result['throughput_rps']} req/s, "
                    f"p50/p95/p99={result['p50_ms']}/{result['p95_ms']}/"
                    f"{result['p99_ms']} ms"
                )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nMachine-readable summary written to {OUTPUT_PATH}")
    return 0 if all(result["error_rate"] == 0 for result in results) else 2


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
    except ValueError as error:
        print(str(error), file=sys.stderr)
        exit_code = 2
    raise SystemExit(exit_code)
