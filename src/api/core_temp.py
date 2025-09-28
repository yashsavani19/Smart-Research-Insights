import os, time, requests, pandas as pd
from dotenv import load_dotenv
from datetime import datetime

# Load CORE API key
load_dotenv()
API_KEY = os.getenv("CORE_API_KEY")
if not API_KEY:
    raise SystemExit("Set CORE_API_KEY in .env as CORE_API_KEY=Bearer <your_key>")

URL = "https://api.core.ac.uk/v3/search/works"
HEADERS = {"Authorization": API_KEY}

# Test query (broad, lots of results). Swap in marine terms later.
Q = "covid"

# Keep field list small to reduce chances of error
SELECT = "id,title,abstract,publishedDate"

PAGE_SIZE = 100     # maximum per request
MIN_WORDS_ABS = 20  # filter abstracts shorter than this


def parse_date(d):
    """Parse date safely, discard nonsense years like 9999"""
    if d:
        try:
            d0 = datetime.fromisoformat(d[:10]).date()
            if d0.year > 2025:
                return ""
            return d0.isoformat()
        except Exception:
            return ""
    return ""


def main():
    print(f"Fetching 1 page of {PAGE_SIZE} works for query: {Q}")

    params = {
        "q": Q,
        "page": 1,
        "pageSize": PAGE_SIZE,
        "select": SELECT,
        "sort": "publishedDate:desc"
    }

    r = requests.get(URL, headers=HEADERS, params=params, timeout=30)
    print("status:", r.status_code)
    if r.status_code != 200:
        print("payload:", r.text[:500])
        return

    data = r.json()
    results = data.get("results", [])
    print("raw results:", len(results))

    rows = []
    for rec in results:
        abs_txt = (rec.get("abstract") or "").strip()
        if len(abs_txt.split()) < MIN_WORDS_ABS:
            continue
        rows.append({
            "id": rec.get("id"),
            "title": rec.get("title"),
            "abstract": abs_txt,
            "published_date": parse_date(rec.get("publishedDate"))
        })

    df = pd.DataFrame(rows).drop_duplicates(subset=["id"])
    os.makedirs("data/exports", exist_ok=True)
    out = "data/exports/papers_for_topics.csv"

    if df.empty:
        print("WARNING: no valid abstracts found. Writing empty CSV with headers.")
        pd.DataFrame(columns=["id","text","published_date"]).to_csv(out, index=False)
    else:
        df[["id","abstract","published_date"]] \
            .rename(columns={"abstract": "text"}) \
            .to_csv(out, index=False)

        print(f"Temporary CSV → {out}  rows={len(df)}")
        print(df.head(5))


if __name__ == "__main__":
    main()
