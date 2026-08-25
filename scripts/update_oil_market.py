import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

OUT = Path("data/oil-market.json")

def get_latest(dataset, frequency, facets):
    key = os.environ.get("EIA_API_KEY")
    if not key:
        raise RuntimeError("EIA_API_KEY is not configured.")
    query = [("api_key", key), ("frequency", frequency), ("data[0]", "value"), ("sort[0][column]", "period"), ("sort[0][direction]", "desc"), ("length", "1")]
    for name, value in facets.items():
        query.append(("facets[{}][]".format(name), value))
    url = "https://api.eia.gov/v2/{}/data/?{}".format(dataset, urlencode(query))
    with urlopen(url, timeout=30) as response:
        rows = json.load(response).get("response", {}).get("data", [])
    if not rows:
        raise RuntimeError("EIA returned no data for {}.".format(dataset))
    return rows[0]

def get_cushing():
    key = os.environ.get("EIA_API_KEY")
    url = "https://api.eia.gov/series/?{}".format(urlencode({"api_key": key, "series_id": "PET.WCESTP11.W"}))
    with urlopen(url, timeout=30) as response:
        series = json.load(response).get("series", [])
    if not series or not series[0].get("data"):
        raise RuntimeError("EIA returned no Cushing data.")
    period, value = series[0]["data"][0]
    return {"period": "{}-{}-{}".format(period[:4], period[4:6], period[6:]), "value": value}

def date_label(value):
    return datetime.strptime(value, "%Y-%m-%d").strftime("%b %-d, %Y")

brent = get_latest("petroleum/pri/spt", "daily", {"series": "RBRTE"})
wti = get_latest("petroleum/pri/spt", "daily", {"series": "RWTC"})
cushing = get_cushing()
data = {
    "brent_display": chr(36) + "{:,.2f}/bbl".format(float(brent["value"])),
    "wti_display": chr(36) + "{:,.2f}/bbl".format(float(wti["value"])),
    "cushing_display": "{:,.3f}M bbl".format(float(cushing["value"]) / 1000),
    "as_of_display": "As of: Brent/WTI {} | Cushing week ending {}".format(date_label(brent["period"]), date_label(cushing["period"])),
    "source": "U.S. Energy Information Administration",
    "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
