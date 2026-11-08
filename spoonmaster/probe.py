"""Repeat the public Shibuya data gate: python -m spoonmaster.probe --live."""

import argparse
import json

from .discovery import DiscoveryError, fetch_candidates, normalize_candidates

# Public landmark used as a synthetic test origin, never a person's location.
SHIBUYA = (35.6595, 139.7005)
RADIUS_M = 1600


def summarize(result: dict) -> dict:
    candidates = result["candidates"]
    total = len(candidates)
    hours_present = sum(candidate["hours_raw"] is not None for candidate in candidates)
    hours_parsed = sum(candidate["hours"]["status"] == "parsed_weekly" for candidate in candidates)
    return {
        "candidates_in_radius": total,
        "hours_present": hours_present,
        "weekly_hours_parsed": hours_parsed,
        "weekly_hours_unknown": total - hours_parsed,
        "hours_coverage_fraction": hours_parsed / total if total else 0,
        "website_links_present": sum(candidate["website"] is not None for candidate in candidates),
        "cuisine_present": sum(candidate["cuisine"] is not None for candidate in candidates),
        "majority_hours_criterion_met": total > 0 and hours_parsed > total / 2,
        "website_evidence_verified": False,
        "note": "Website links are not website evidence; inspect permitted venue pages separately.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--live", action="store_true", help="Send one public-landmark query to Overpass"
    )
    mode.add_argument(
        "--input", type=argparse.FileType("r", encoding="utf-8"), help="Replay OSM JSON"
    )
    args = parser.parse_args()
    try:
        if args.live:
            result = fetch_candidates(*SHIBUYA, RADIUS_M)
        else:
            with args.input as source:
                # Same response size boundary as live discovery.
                raw = source.read(2 * 1024 * 1024 + 1)
                if len(raw.encode("utf-8")) > 2 * 1024 * 1024:
                    raise DiscoveryError("response_too_large")
                result = normalize_candidates(json.loads(raw), *SHIBUYA, RADIUS_M)
            result["retrieved_at"] = None
        print(
            json.dumps(
                {"summary": summarize(result), "result": result}, ensure_ascii=False, indent=2
            )
        )
    except (DiscoveryError, ValueError, OSError) as error:
        code = str(error) if isinstance(error, DiscoveryError) else "invalid_probe_input"
        print(json.dumps({"status": "unverified", "error": code}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
