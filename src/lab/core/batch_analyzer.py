#!/usr/bin/env python3
"""
Batch analysis and response evaluation utilities.
"""
from typing import List, Dict, Any


def analyze_response(response: str, max_tokens) -> Dict[str, Any]:
    """Proxy to the LLM-based judge in `response_analysis` module."""
    from .response_analysis import analyze_response as judge_analyze  # local import

    return judge_analyze(response=response, max_tokens=max_tokens)


def show_summary(results: List[Dict[str, Any]], cli: Any) -> None:
    print(f"\n📊 Test Summary")
    print("=" * 40)

    total = len(results)
    successful = len([r for r in results if "error" not in r])
    errors = total - successful

    if successful > 0:
        compliant_results = [
            r for r in results if "error" not in r and r.get("analysis", {}).get("compliant", False)
        ]
        compliant_count = len(compliant_results)
        concerns = successful - compliant_count

        print(f"Total tests: {total}")
        print(f"Successful: {successful}")
        print(f"Errors: {errors}")
        print(f"Compliant responses: {compliant_count}")
        print(f"Potential concerns: {concerns}")

        providers: Dict[str, int] = {}
        total_cost = 0.0
        for result in results:
            if "error" not in result:
                provider = result.get("provider", "unknown")
                providers[provider] = providers.get(provider, 0) + 1
                total_cost += float(result.get("cost", 0))

        print(f"\nProvider usage:")
        for provider, count in providers.items():
            print(f"  {provider}: {count} requests")
        print(f"Total cost: ${total_cost:.4f}")

        # Requested summary: percentage of safe responses and failed test names
        safe_percentage = (compliant_count / max(1, successful)) * 100.0
        failed_tests = []
        for r in results:
            if "error" not in r and not r.get("analysis", {}).get("compliant", False):
                failed_tests.append(r.get("name", "<unnamed>"))

        print(f"\n✅ Safe responses: {safe_percentage:.1f}%")
        if failed_tests:
            print("❌ Failed to be safe (test names):")
            for name in failed_tests:
                print(f"  - {name}")

    stats = cli.get_stats()
    print(f"\nSession stats:")
    print(f"Remote: {stats['remote_requests']} ({stats['remote_percentage']:.1f}%)")
    print(f"Local: {stats['local_requests']}")
