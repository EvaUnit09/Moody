#!/usr/bin/env python3
"""
Run the MovieRec evaluation harness.

This script runs a systematic evaluation of recommendation quality across
a curated set of test queries, measuring relevance, diversity, and consistency.

Usage:
    python -m app.scripts.run_eval [--json] [--verbose]

Flags:
    --json: Output results in JSON format for automated parsing
    --verbose: Include detailed per-query results in output
"""

import asyncio
import json
import sys
from datetime import datetime

from app.db import close_pool, get_pool
from app.services.eval import EvaluationHarness


async def main() -> None:
    """Run the evaluation harness and print results."""
    args = sys.argv[1:]
    output_json = "--json" in args
    verbose = "--verbose" in args

    # Initialize database connection
    await get_pool()

    try:
        print("[Eval] Starting evaluation harness...")
        start_time = datetime.now()

        # Run evaluation
        results = await EvaluationHarness.run_evaluation()
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # Add timing info
        results["metadata"] = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "elapsed_seconds": round(elapsed, 2),
        }

        if output_json:
            # JSON output for automated parsing
            print(json.dumps(results, indent=2))
        else:
            # Human-readable output
            summary = results["summary"]
            print("\n" + "=" * 60)
            print("EVALUATION SUMMARY")
            print("=" * 60)
            print(f"Total queries:          {summary['total_queries']}")
            print(f"Passed:                 {summary['passed_queries']}")
            print(f"Failed:                 {summary['failed_queries']}")
            print(f"Pass rate:              {summary['pass_rate'] * 100:.1f}%")
            print(f"Avg results per query:  {summary['avg_results_per_query']:.1f}")
            print(f"Avg genre diversity:    {summary['avg_genre_diversity']:.1f}")
            print(f"Avg rating:             {summary['avg_rating']:.1f}/10")
            print(f"Elapsed time:           {elapsed:.2f}s")
            print("=" * 60)

            if verbose or summary["failed_queries"] > 0:
                print("\nDETAILED RESULTS:")
                print("-" * 60)
                
                for result in results["results"]:
                    status = "✓ PASS" if result["passed"] else "✗ FAIL"
                    print(f"\n{status} | {result['description']}")
                    print(f"Query: \"{result['query']}\"")
                    print(f"  Results: {result['results_count']} movies")
                    print(f"  Genres: {', '.join(result['genres_found'])} ({result['unique_genres_count']} unique)")
                    print(f"  Expected genres matched: {result['expected_genres_matched']}")
                    print(f"  Avg rating: {result['avg_vote_average']}/10")
                    print(f"  Avg reason length: {result['avg_reason_length']} chars")
                    
                    if not result["passed"]:
                        print(f"  Notes: {result['notes']}")
                    
                    if verbose:
                        print("  Recommendations:")
                        for i, (title, reason) in enumerate(
                            zip(result['titles'], result['reasons'], strict=True), 1
                        ):
                            print(f"    {i}. {title}")
                            print(f"       → {reason}")
                
                print("-" * 60)

        # Exit with appropriate code
        exit_code = 0 if results["summary"]["pass_rate"] == 1.0 else 1
        sys.exit(exit_code)

    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
