#!/usr/bin/env python3
"""Compare the neuron ledger with Cloudflare's Workers AI usage, one row per UTC day. Read-only.

Cloudflare: hourly ``totalNeurons`` (GraphQL ``aiInferenceAdaptiveGroups``); token from ``CLOUDFLARE_ANALYTICS``,
account from ``CLOUDFLARE_ACCOUNT_ID``, neither printed. Ledger: ``budget show --resource neurons``, which returns
only the current UTC period, so a past day prints ``n/a`` in the ledger column.

    python3 scripts/neuron_reconcile.py --from 2026-10-30 --to 2026-11-13
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

DISCOVERY_DIR = Path(__file__).resolve().parents[1] / "apps" / "discovery-ingest"
QUERY = (
    "query ($tag: string, $from: Time, $to: Time) { viewer { accounts(filter: { accountTag: $tag }) {"
    " aiInferenceAdaptiveGroups(limit: 10000, filter: { datetime_geq: $from, datetime_lt: $to })"
    " { sum { totalNeurons } dimensions { datetimeHour } } } } }"
)


def cloudflare_hourly(start: date, end: date) -> dict[str, float]:
    """Return Cloudflare's neurons per UTC hour (``YYYY-MM-DDTHH:00:00Z``) from ``start`` up to ``end``, exclusive."""
    token, account = os.environ.get("CLOUDFLARE_ANALYTICS"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    if not token or not account:
        sys.exit("set CLOUDFLARE_ANALYTICS and CLOUDFLARE_ACCOUNT_ID in the environment")
    variables = {"tag": account, "from": f"{start}T00:00:00Z", "to": f"{end}T00:00:00Z"}
    body = json.dumps({"query": QUERY, "variables": variables}).encode()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    request = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", body, headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get("errors"):
        sys.exit(f"Cloudflare GraphQL error: {payload['errors'][0].get('message', 'unknown')}")
    hourly: defaultdict[str, float] = defaultdict(float)
    for group in payload["data"]["viewer"]["accounts"][0]["aiInferenceAdaptiveGroups"]:
        hourly[group["dimensions"]["datetimeHour"]] += float(group["sum"]["totalNeurons"] or 0)
    return dict(hourly)


def ledger_neurons(python: str) -> dict[str, float]:
    """Return ``{period: used}`` for the neurons row the ledger reports now; empty when it does not answer."""
    cli = [python, "-m", "discovery_ingest", "budget", "show", "--resource", "neurons"]
    result = subprocess.run(cli, cwd=DISCOVERY_DIR, capture_output=True, text=True, check=False)
    try:
        items = json.loads(result.stdout)["items"]
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"ledger did not answer: {result.stderr.strip()[:200]}", file=sys.stderr)
        return {}
    return {row["period"]: float(row["used"]) for row in items if row["resource"] == "neurons"}


def main() -> None:
    """Print one reconciliation row per UTC day from ``--from`` to ``--to``, both inclusive."""
    parser = argparse.ArgumentParser(description="Neuron ledger against Cloudflare usage, per UTC day.")
    parser.add_argument("--from", dest="start", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    parser.add_argument("--to", dest="end", type=date.fromisoformat, required=True, help="YYYY-MM-DD")
    venv = DISCOVERY_DIR / ".venv" / "bin" / "python"
    parser.add_argument("--python", default=str(venv if venv.exists() else sys.executable), help="CLI interpreter")
    args = parser.parse_args()
    days = [args.start + timedelta(days=n) for n in range((args.end - args.start).days + 1)]
    cloudflare: defaultdict[str, float] = defaultdict(float)
    for hour, neurons in cloudflare_hourly(args.start, args.end + timedelta(days=1)).items():
        cloudflare[hour[:10]] += neurons
    ledger = ledger_neurons(args.python)
    print("| UTC day | ledger used | Cloudflare used | ledger minus Cloudflare |")
    print("| --- | ---: | ---: | ---: |")
    for day in days:
        key, used = day.isoformat(), ledger.get(day.isoformat())
        if used is None:
            print(f"| {key} | n/a | {cloudflare[key]:,.2f} | n/a |")
        else:
            print(f"| {key} | {used:,.2f} | {cloudflare[key]:,.2f} | {used - cloudflare[key]:,.2f} |")


if __name__ == "__main__":
    main()
