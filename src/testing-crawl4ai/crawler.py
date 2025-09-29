

# -*- coding: utf-8 -*-
"""
Fetch AU/NZ marine-tech research from OpenAlex for the last 5 years.
Outputs: CSV + JSONL with title, abstract, DOI, URL, date, institutions, concepts.

Run:
    python get_openalex_5y.py
"""

import csv
import json
import time
import datetime as dt
from urllib.parse import urlencode
import requests

# ---------------------------------------------------------
# CONFIG — tweak as you like
# ---------------------------------------------------------

# A single broad query that covers your marine/ocean anchors + tech themes.
QUERY = (
    '('
    'marine OR ocean OR offshore OR maritime OR naval OR ship OR aquaculture'
    ') AND ('
    # Autonomy / AI / inspection
    '"autonomous underwater vehicle" OR AUV OR ROV OR ASV OR USV OR autonomous OR "path planning" OR SLAM OR "computer vision" OR "defect detection" OR "predictive maintenance" OR "condition-based maintenance" OR CBM OR "digital twin" OR "data fusion" OR "edge computing" OR "multi-sensor fusion" OR "time-series anomaly detection" OR "change detection"'
    ' OR '
    # Sensors / comms
    'sonar OR "acoustic sensing" OR "ultrasonic" OR "multibeam echosounder" OR "sidescan sonar" OR "underwater acoustic communication" OR "optical modem" OR "blue-green laser" OR "acoustic modem"'
    ' OR '
    # Energy / sustainability
    '"marine renewable energy" OR "wave energy" OR "wave energy converter" OR "tidal turbine" OR "offshore wind" OR "floating wind" OR "battery thermal management" OR "energy efficiency" OR "air lubrication" OR "life cycle assessment"'
    ' OR '
    # Materials / coatings
    '"corrosion resistant" OR antifouling OR biofouling OR "marine coatings" OR "cathodic protection" OR CFRP OR GFRP'
    ' OR '
    # Data / navigation
    '"AIS analytics" OR "vessel trajectory" OR "trajectory prediction"'
    ')'
)

# AU/NZ focus
COUNTRY_FILTER = "AU|NZ"    # filter by author institutions’ country (Australia/New Zealand)

# Time window: last 5 years
DAYS_BACK = 5 * 365

since_date = dt.date.fromisoformat("2019-01-01")

# OpenAlex page size & politeness
PER_PAGE = 200              # OpenAlex max per_page=200
PAUSE_SEC = 0.25            # short delay between pages

# Output files
OUTPUT_CSV = "openalex_papers_5y.csv"
OUTPUT_JSONL = "openalex_papers_5y.jsonl"

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def reconstruct_openalex_abstract(inv_idx: dict) -> str:
    """Rebuild plain-text abstract from OpenAlex's inverted index, if needed."""
    pairs = [(pos, token) for token, positions in inv_idx.items() for pos in positions]
    pairs.sort(key=lambda x: x[0])
    return " ".join(tok for _, tok in pairs)

def normalize_work(w: dict) -> dict:
    """
    Convert an OpenAlex 'work' result to a consistent row for CSV/JSONL.
    """
    abstract = w.get("abstract") or ""
    if not abstract and w.get("abstract_inverted_index"):
        abstract = reconstruct_openalex_abstract(w["abstract_inverted_index"])

    url = (w.get("primary_location") or {}).get("landing_page_url") or w.get("id")
    pub_date = (w.get("publication_date") or "")[:10] or None

    return {
        "title": w.get("title") or "",
        "abstract": abstract or "",
        "doi": w.get("doi"),
        "url": url,
        "source": "openalex",
        "published_date": pub_date,
        "institutions": w.get("authorships") or [],
        "concepts": w.get("concepts") or [],
    }

# ---------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------

def fetch_openalex_5y():
    base = "https://api.openalex.org/works"

    filters = [
        f'from_publication_date:{since_date}',
        'has_abstract:true',
        f'institutions.country_code:{COUNTRY_FILTER}',
        f'to_publication_date:{dt.date.today()}',
    ]

    params = {
        "search": QUERY,
        "filter": ",".join(filters),
        "per_page": PER_PAGE,
        "cursor": "*",
        # "sort": "publication_date:desc",  # optional
    }

    print("\n=== OpenAlex 5-year fetch ===")
    print("Query:\n ", QUERY)
    print("Filters:\n ", filters)
    print("Output:\n ", OUTPUT_CSV, "and", OUTPUT_JSONL, "\n")

    total = 0

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_csv, \
         open(OUTPUT_JSONL, "w", encoding="utf-8") as f_jsonl:
        writer = csv.writer(f_csv)
        writer.writerow([
            "title", "abstract", "doi", "url",
            "source", "published_date", "institutions", "concepts"
        ])

        while True:
            url = f"{base}?{urlencode(params)}"
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            data = r.json()

            results = data.get("results", [])
            if not results:
                break

            for w in results:
                row = normalize_work(w)

                writer.writerow([
                    row["title"], row["abstract"], row["doi"], row["url"],
                    row["source"], row["published_date"],
                    json.dumps(row["institutions"], ensure_ascii=False),
                    json.dumps(row["concepts"], ensure_ascii=False),
                ])
                f_jsonl.write(json.dumps(row, ensure_ascii=False) + "\n")
                total += 1

            print(f"  +{len(results)} (total: {total})")
            next_cursor = (data.get("meta") or {}).get("next_cursor")
            if not next_cursor:
                break

            params["cursor"] = next_cursor
            time.sleep(PAUSE_SEC)

    print(f"\n✅ Done. Wrote {total} rows → {OUTPUT_CSV} and {OUTPUT_JSONL}")
    return total

# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    fetch_openalex_5y()
