"""Publish the latest EIA oil market values for the Shopify header ticker."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


API_ROOT = "https://api.eia.gov/v2"
OUTPUT_FILE = Path("data/oil-market.json")


def get_latest(dataset: str, frequency: str, facets: dict[str, str]) -> dict:
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        raise RuntimeError("EIA_API_KEY is not configured.")

    query: list[tuple[str, str]] = [
        ("api_key", api_key),
        ("frequency", frequency),
        ("data[0]", "value"),
        ("sort[0][column]", "period"),
        ("sort[0][direction]", "desc"),
        ("length", "1"),
    ]
    for name, value in facets.items():
        query.append((f"facets[{name}][]", value))

    url = f"{API_ROOT}/{dataset}/data/?{urlencode(query)}"
    with urlopen(url, timeout=30) as response:
        payload = json.load(response)

    rows = payload.get("response", {}).get("data", [])
    if not rows:
        raise RuntimeError(f"EIA returned no data for {dataset}.")
    return rows[0]


def format_date(value: str) -> str:
    return datetime.strptime(value, "%Y-%m-%d").strftime("%b %-d, %Y")


def main() -> None:
    brent = get_latest("petroleum/pri/spt", "daily", {"series": "RBRTE"})
    wti = get_latest("petroleum/pri/spt", "daily", {"series": "RWTC"})
    cushing = get_latest(
        "petroleum/stoc/wstk",
        "weekly",
        {"productId": "EPC0", "areaId": "YCUOK"},
    )

    brent_value = float(brent["value"])
    wti_value = float(wti["value"])
    cushing_thousand_barrels = float(cushing["value"])

    data = {
        "brent_display": f"${brent_value:,.2f}/bbl",
        "wti_display": f"${wti_value:,.2f}/bbl",
        "cushing_display": f"{cushing_thousand_barrels / 1000:,.3f}M bbl",
        "as_of_display": (
            f"As of: Brent/WTI {format_date(brent['period'])} | "
            f"Cushing week ending {format_date(cushing['period'])}"
        ),
        "source": "U.S. Energy Information Administration",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
