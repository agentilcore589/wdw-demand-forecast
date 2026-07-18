"""
Pull daily weather (actuals + 14-day forecast) for the WDW area from Open-Meteo.
Free, no API key. Appends to data/external/weather.csv, deduped by (date, kind).

Lake Buena Vista, FL: 28.3852, -81.5639
"""

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAT, LON = 28.3852, -81.5639
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "external"
OUTFILE = DATA_DIR / "weather.csv"

URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "precipitation_probability_max,wind_speed_10m_max"
    "&temperature_unit=fahrenheit&precipitation_unit=inch"
    "&timezone=America%2FNew_York&past_days=7&forecast_days=14"
)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "wdw-demand-forecast"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    daily = data["daily"]
    pulled = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()

    rows = []
    for i, date in enumerate(daily["time"]):
        rows.append(
            {
                "date": date,
                "kind": "actual" if date < today else "forecast",
                "pulled_at_utc": pulled,
                "temp_max_f": daily["temperature_2m_max"][i],
                "temp_min_f": daily["temperature_2m_min"][i],
                "precip_in": daily["precipitation_sum"][i],
                "precip_prob_max": daily["precipitation_probability_max"][i],
                "wind_max_mph": daily["wind_speed_10m_max"][i],
            }
        )

    # Load existing, overwrite same-date rows with the freshest pull
    existing = {}
    fieldnames = list(rows[0].keys())
    if OUTFILE.exists():
        with open(OUTFILE, newline="") as f:
            for r in csv.DictReader(f):
                existing[r["date"]] = r

    for r in rows:
        existing[r["date"]] = {k: str(v) for k, v in r.items()}

    with open(OUTFILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for date in sorted(existing):
            writer.writerow(existing[date])

    print(f"Weather file now has {len(existing)} dates")


if __name__ == "__main__":
    main()
