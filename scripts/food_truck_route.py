#!/usr/bin/env python3
"""Run the food-truck weekly route planner end-to-end.

Loads the customer fixture, runs the deterministic clustering + content
drafting + projection, and writes a JSON + Markdown artifact pair to
``evidence/`` (or wherever ``--out-dir`` points).

This is the marketing-agent's "weekly capability" demo. The agent itself
would normally call the same module via ``Read``/``Bash`` from inside
``claude -p``; here we expose the driver standalone so the artifact is
reproducible without spinning up an LLM call.

Usage:

    python scripts/food_truck_route.py
    python scripts/food_truck_route.py --seed 42 --k 5
    python scripts/food_truck_route.py --stem food-truck-route-sample
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from orchestrator.food_truck_route import (  # noqa: E402
    build_route,
    load_customers,
    write_artifacts,
)

DEFAULT_FIXTURE = REPO_ROOT / "orchestrator" / "fixtures" / "food_truck_customers.json"
DEFAULT_OUT_DIR = REPO_ROOT / "evidence"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--k", type=int, default=5, help="Number of clusters / weekday stops")
    parser.add_argument("--seed", type=int, default=7, help="k-means seed (deterministic)")
    parser.add_argument(
        "--stem",
        type=str,
        default=None,
        help="File stem (default: timestamped). Use 'food-truck-route-sample' for a stable artifact.",
    )
    parser.add_argument(
        "--at",
        type=str,
        default=None,
        help="Generated-at ISO timestamp (default: now UTC). Use a fixed value for reproducible artifacts.",
    )
    args = parser.parse_args()

    customers = load_customers(args.fixture)
    stops = build_route(customers, k=args.k, seed=args.seed)
    iso = args.at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json_path, md_path, route = write_artifacts(
        stops,
        out_dir=args.out_dir,
        generated_at_iso=iso,
        file_stem=args.stem,
    )

    s = route["summary"]
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(
        f"Stops: {s['stops']} · Customers: {s['customers']} · "
        f"Δ orders/mo: {s['incrementalOrdersMonth']} · "
        f"Δ revenue/mo: ${s['incrementalRevenueMonthUsd']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
