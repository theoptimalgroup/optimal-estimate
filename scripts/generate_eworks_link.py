#!/usr/bin/env python3
"""Generate a signed eWorks calculation link for local testing."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.eworks_link_service import build_signed_test_link  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an eWorks /eworks/calculate link")
    parser.add_argument("--base-url", default=os.environ.get("FRONTEND_URL", "http://localhost:3000"))
    parser.add_argument("--quote-number", default="Q21863")
    parser.add_argument("--job-number", default="33629")
    parser.add_argument("--client", default="Lambert Chartered Surveyors")
    parser.add_argument("--trade", default="Carpenter")
    parser.add_argument("--address", default="The Factory, 1 Nile Street")
    parser.add_argument("--engineer", default="Alex Alves")
    parser.add_argument("--days-valid", type=int, default=30)
    parser.add_argument(
        "--write-file",
        default=str(ROOT / "docs" / "test-eworks-link.txt"),
        help="Write the full URL to this file (default: docs/test-eworks-link.txt)",
    )
    args = parser.parse_args()

    _, _, payload, url = build_signed_test_link(
        quote_number=args.quote_number,
        job_number=args.job_number,
        client=args.client,
        trade=args.trade,
        property_address=args.address,
        engineer_name=args.engineer,
        days_valid=args.days_valid,
        frontend_url=args.base_url,
    )

    if args.write_file:
        out_path = Path(args.write_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(url + "\n", encoding="utf-8")

    print("Signed eWorks calculation link:\n")
    print(url)
    if args.write_file:
        print(f"\nFull URL saved to: {args.write_file}")
    print("\nOpen the full URL above in your browser. Do not truncate or shorten it.")
    print("\nPayload JSON:")
    import json

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
