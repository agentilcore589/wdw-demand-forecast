"""
Pull current wait times for all four WDW parks from the queue-times.com API.
Appends one snapshot per run to data/raw/waits_YYYY-MM.csv (monthly files).

Run via GitHub Actions on a cron (see .github/workflows/pull.yml).
API docs: https://queue-times.com/pages/api
Attribution required by their terms: "Powered by Queue-Times.com"
"""

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://queue-times.com"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Walt Disney World park names as they appear in the API's parks.json
WDW_PARKS = {
    "Disney Magic Kingdom",
    "Epcot",
    "Disney Hollywood Studios",
    "Animal Kingdom",
}


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "wdw-demand-forecast"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def discover_park_ids() -> dict:
    """Find WDW park IDs by name so we never rely on hardcoded IDs."""
    groups = fetch_json(f"{BASE}/parks.json")
    ids = {}
    for group in groups:
        for park in group.get("parks", []):
            if park["name"] in WDW_PARKS:
                ids[park["name"]] = park["id"]
    missing = WDW_PARKS - set(ids)
    if missing:
        raise RuntimeError(f"Could not find parks in API: {missing}")
    return ids


def pull_park(park_id: int) -> list[dict]:
    data = fetch_json(f"{BASE}/parks/{park_id}/queue_times.json")
    rows = []
    ts = datetime.now(timezone.utc).isoformat()
    # Rides live under lands[].rides[] and sometimes a top-level rides[]
    lands = data.get("lands", [])
    all_rides = [r for land in lands for r in land.get("rides", [])]
    all_rides += data.get("rides", [])
    for ride in all_rides:
        rows.append(
            {
                "pulled_at_utc": ts,
                "park_id": park_id,
                "ride_id": ride.get("id"),
                "ride_name": ride.get("name"),
                "is_open": ride.get("is_open"),
                "wait_time_min": ride.get("wait_time"),
                "last_updated": ride.get("last_updated"),
            }
        )
    return rows


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    park_ids = discover_park_ids()

    all_rows = []
    for name, pid in park_ids.items():
        rows = pull_park(pid)
        for r in rows:
            r["park_name"] = name
        all_rows.extend(rows)
        print(f"{name}: {len(rows)} rides")

    outfile = DATA_DIR / f"waits_{datetime.now(timezone.utc):%Y-%m}.csv"
    write_header = not outfile.exists()
    fieldnames = [
        "pulled_at_utc", "park_id", "park_name", "ride_id",
        "ride_name", "is_open", "wait_time_min", "last_updated",
    ]
    with open(outfile, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(all_rows)

    print(f"Appended {len(all_rows)} rows to {outfile.name}")


if __name__ == "__main__":
    main()
