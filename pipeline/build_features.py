"""
Build the daily modeling table from raw intraday pulls.

Reads:  data/raw/waits_*.csv        (intraday ride-level snapshots)
        data/external/weather.csv   (daily weather, actuals + forecast)
        data/external/calendar_events.csv  (holidays, breaks, events)

Writes: data/processed/daily.csv    (one row per park per day, modeling-ready)

Run locally or add to the GitHub Actions workflow later. Stdlib only.
"""

import csv
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
EXT = ROOT / "data" / "external"
OUT = ROOT / "data" / "processed"
EASTERN = ZoneInfo("America/New_York")


def load_snapshots():
    """Yield (park_name, local_date, wait_time) for open rides with a posted wait."""
    for f in sorted(RAW.glob("waits_*.csv")):
        with open(f, newline="") as fh:
            for row in csv.DictReader(fh):
                wait = row.get("wait_time_min")
                if row.get("is_open") != "True" or wait in ("", "None", None):
                    continue
                ts = datetime.fromisoformat(row["pulled_at_utc"])
                local_day = ts.astimezone(EASTERN).date()
                yield row["park_name"], local_day, float(wait)


def aggregate_daily():
    """Park-day aggregates: mean/max wait, snapshot coverage."""
    sums = defaultdict(float)
    counts = defaultdict(int)
    maxes = defaultdict(float)
    for park, day, wait in load_snapshots():
        key = (park, day)
        sums[key] += wait
        counts[key] += 1
        maxes[key] = max(maxes[key], wait)
    rows = {}
    for key in sums:
        park, day = key
        rows[key] = {
            "date": day.isoformat(),
            "park_name": park,
            "avg_wait": round(sums[key] / counts[key], 2),
            "max_wait": maxes[key],
            "n_observations": counts[key],
        }
    return rows


def load_keyed_csv(path, key_field):
    if not path.exists():
        return {}
    with open(path, newline="") as fh:
        return {r[key_field]: r for r in csv.DictReader(fh)}


def load_events():
    """calendar_events.csv: date ranges -> set of event flags per date."""
    path = EXT / "calendar_events.csv"
    flags = defaultdict(set)
    if not path.exists():
        return flags
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            start = date.fromisoformat(r["start_date"])
            end = date.fromisoformat(r["end_date"] or r["start_date"])
            d = start
            while d <= end:
                flags[d.isoformat()].add(r["event_type"])
                d += timedelta(days=1)
    return flags

EVENT_TYPES = ["federal_holiday", "school_break", "rundisney", "mk_party", "other_event"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    daily = aggregate_daily()
    weather = load_keyed_csv(EXT / "weather.csv", "date")
    events = load_events()

    fieldnames = [
        "date", "park_name", "avg_wait", "max_wait", "n_observations",
        "day_of_week", "is_weekend", "week_of_year",
        "temp_max_f", "precip_prob_max",
    ] + [f"is_{e}" for e in EVENT_TYPES]

    with open(OUT / "daily.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for key in sorted(daily):
            row = daily[key]
            d = date.fromisoformat(row["date"])
            row["day_of_week"] = d.strftime("%a")
            row["is_weekend"] = int(d.weekday() >= 5)
            row["week_of_year"] = d.isocalendar().week
            w = weather.get(row["date"], {})
            row["temp_max_f"] = w.get("temp_max_f", "")
            row["precip_prob_max"] = w.get("precip_prob_max", "")
            day_flags = events.get(row["date"], set())
            for e in EVENT_TYPES:
                row[f"is_{e}"] = int(e in day_flags)
            writer.writerow(row)

    print(f"Wrote {len(daily)} park-day rows to data/processed/daily.csv")


if __name__ == "__main__":
    main()
