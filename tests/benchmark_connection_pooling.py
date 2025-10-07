#!/usr/bin/env python3
"""
Benchmark script for connection pooling

Measures actual performance improvement with Dify API
Requires Dify instance running at http://localhost:8088
"""

import sys
import os
import time
from statistics import mean, stdev

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.dify_api_resilient import ResilientDifyAPI
from dotenv import load_dotenv

load_dotenv()


def benchmark_api_calls(enable_pooling: bool, num_calls: int = 50):
    """
    Benchmark API calls with/without connection pooling

    Args:
        enable_pooling: Whether to enable connection pooling
        num_calls: Number of API calls to make

    Returns:
        dict with timing results
    """
    api = ResilientDifyAPI(
        base_url=os.getenv('DIFY_BASE_URL', 'http://localhost:8088'),
        api_key=os.getenv('DIFY_API_KEY'),
        enable_connection_pooling=enable_pooling,
        enable_retry=False,  # Disable retry for accurate timing
        enable_circuit_breaker=False
    )

    # Warm-up call (first call includes DNS lookup, connection setup)
    try:
        api.get_knowledge_base_list()
    except Exception as e:
        print(f"⚠️  Warm-up call failed: {e}")
        return None

    # Measure subsequent calls
    call_times = []

    for i in range(num_calls):
        start = time.perf_counter()
        try:
            response = api.get_knowledge_base_list()
            elapsed = time.perf_counter() - start
            call_times.append(elapsed)

            if response.status_code != 200:
                print(f"⚠️  Call {i+1} returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️  Call {i+1} failed: {e}")
            call_times.append(None)

    # Filter out failed calls
    valid_times = [t for t in call_times if t is not None]

    if not valid_times:
        return None

    return {
        'total_calls': num_calls,
        'successful_calls': len(valid_times),
        'total_time': sum(valid_times),
        'avg_time': mean(valid_times),
        'min_time': min(valid_times),
        'max_time': max(valid_times),
        'std_dev': stdev(valid_times) if len(valid_times) > 1 else 0,
        'times': valid_times
    }


def print_results(pooling_results, no_pooling_results):
    """Print formatted benchmark results"""

    print("\n" + "="*70)
    print("📊 CONNECTION POOLING BENCHMARK RESULTS")
    print("="*70)

    if no_pooling_results:
        print("\n🐢 WITHOUT Connection Pooling:")
        print(f"   Total Time:     {no_pooling_results['total_time']:.3f}s")
        print(f"   Average Time:   {no_pooling_results['avg_time']*1000:.1f}ms per call")
        print(f"   Min Time:       {no_pooling_results['min_time']*1000:.1f}ms")
        print(f"   Max Time:       {no_pooling_results['max_time']*1000:.1f}ms")
        print(f"   Std Dev:        {no_pooling_results['std_dev']*1000:.1f}ms")
        print(f"   Success Rate:   {no_pooling_results['successful_calls']}/{no_pooling_results['total_calls']}")

    if pooling_results:
        print("\n🚀 WITH Connection Pooling:")
        print(f"   Total Time:     {pooling_results['total_time']:.3f}s")
        print(f"   Average Time:   {pooling_results['avg_time']*1000:.1f}ms per call")
        print(f"   Min Time:       {pooling_results['min_time']*1000:.1f}ms")
        print(f"   Max Time:       {pooling_results['max_time']*1000:.1f}ms")
        print(f"   Std Dev:        {pooling_results['std_dev']*1000:.1f}ms")
        print(f"   Success Rate:   {pooling_results['successful_calls']}/{pooling_results['total_calls']}")

    if pooling_results and no_pooling_results:
        print("\n📈 IMPROVEMENT:")
        time_saved = no_pooling_results['total_time'] - pooling_results['total_time']
        percent_faster = (time_saved / no_pooling_results['total_time']) * 100
        speedup = no_pooling_results['avg_time'] / pooling_results['avg_time']

        print(f"   Time Saved:     {time_saved:.3f}s ({percent_faster:.1f}%)")
        print(f"   Speedup:        {speedup:.2f}x")
        print(f"   Avg Improvement: {(no_pooling_results['avg_time'] - pooling_results['avg_time'])*1000:.1f}ms per call")

        # Per-call comparison
        avg_per_call_saving = time_saved / pooling_results['successful_calls']
        print(f"\n💡 Savings per call: {avg_per_call_saving*1000:.1f}ms")

        # Projection for large crawls
        print(f"\n🎯 For 200-page crawl (600 API calls):")
        print(f"   Time saved: {time_saved * 12:.1f}s ({percent_faster:.1f}%)")

    print("="*70)


def run_benchmark(num_calls: int = 50):
    """Run complete benchmark"""

    print("\n" + "="*70)
    print("🏁 STARTING CONNECTION POOLING BENCHMARK")
    print("="*70)
    print(f"Number of API calls: {num_calls}")
    print(f"Dify URL: {os.getenv('DIFY_BASE_URL', 'http://localhost:8088')}")
    print()

    # Test connection first
    print("🔍 Testing Dify connection...")
    try:
        test_api = ResilientDifyAPI(
            base_url=os.getenv('DIFY_BASE_URL', 'http://localhost:8088'),
            api_key=os.getenv('DIFY_API_KEY'),
            enable_retry=False
        )
        response = test_api.get_knowledge_base_list()
        print(f"✅ Connection successful (status: {response.status_code})")
    except Exception as e:
        print(f"❌ Cannot connect to Dify: {e}")
        print("\nMake sure:")
        print("  1. Dify is running at http://localhost:8088")
        print("  2. DIFY_API_KEY is set in .env file")
        return

    # Benchmark WITHOUT pooling
    print(f"\n🐢 Running {num_calls} calls WITHOUT connection pooling...")
    no_pooling_results = benchmark_api_calls(enable_pooling=False, num_calls=num_calls)

    # Small delay between tests
    time.sleep(1)

    # Benchmark WITH pooling
    print(f"🚀 Running {num_calls} calls WITH connection pooling...")
    pooling_results = benchmark_api_calls(enable_pooling=True, num_calls=num_calls)

    # Print results
    print_results(pooling_results, no_pooling_results)

    # Save results to file
    if pooling_results and no_pooling_results:
        save_results(pooling_results, no_pooling_results)


def save_results(pooling_results, no_pooling_results):
    """Save benchmark results to JSON file"""
    import json
    from datetime import datetime

    results = {
        'timestamp': datetime.now().isoformat(),
        'without_pooling': {
            'total_time': no_pooling_results['total_time'],
            'avg_time_ms': no_pooling_results['avg_time'] * 1000,
            'successful_calls': no_pooling_results['successful_calls']
        },
        'with_pooling': {
            'total_time': pooling_results['total_time'],
            'avg_time_ms': pooling_results['avg_time'] * 1000,
            'successful_calls': pooling_results['successful_calls']
        },
        'improvement': {
            'time_saved': no_pooling_results['total_time'] - pooling_results['total_time'],
            'percent_faster': ((no_pooling_results['total_time'] - pooling_results['total_time']) / no_pooling_results['total_time']) * 100,
            'speedup': no_pooling_results['avg_time'] / pooling_results['avg_time']
        }
    }

    os.makedirs('output', exist_ok=True)
    with open('output/connection_pooling_benchmark.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: output/connection_pooling_benchmark.json")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Benchmark connection pooling performance')
    parser.add_argument(
        '--calls',
        type=int,
        default=50,
        help='Number of API calls to make (default: 50)'
    )

    args = parser.parse_args()

    run_benchmark(num_calls=args.calls)
