# src/core_client/works_scroll.py
# Scroll query for CORE "works" with:
# - field auto-detection (dataProviders / dataProviders.id / repositories / repositories.id)
# - batched OR clauses to avoid boolean clause limits
# - yearPublished range (safe) + your marine terms

import os, json, time, requests
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CORE_API_KEY")
if not API_KEY:
    raise RuntimeError("Set CORE_API_KEY in .env (include 'Bearer ' prefix).")

BASE = "https://api.core.ac.uk/v3/"
HEADERS = {"Authorization": API_KEY, "Content-Type": "application/json"}

MARINE_TERMS = (
  '"marine robotics" OR "autonomous underwater vehicle" OR AUV OR ROV OR sonar OR hydrophone '
  'OR bathymetry OR "underwater acoustics" OR aquaculture OR "offshore structures" OR corrosion OR biofouling'
)

def _post(endpoint: str, body: dict, retries: int = 5, timeout: int = 60) -> dict:
    for i in range(retries):
        r = requests.post(BASE + endpoint, headers=HEADERS, data=json.dumps(body), timeout=timeout)
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                return {}
            if "results" in data:
                return data
            # some shards wrap JSON in "message"
            if "message" in data:
                try:
                    return json.loads(data["message"])
                except Exception:
                    return {}
            return {}
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"[retry {i}] CORE {r.status_code}: {r.text[:120]}")
            time.sleep(2 ** i)
            continue
        raise RuntimeError(f"CORE {r.status_code}: {r.text[:200]}")
    raise RuntimeError("CORE: max retries")

def detect_provider_field(one_provider_id: int) -> str:
    """
    Try a single provider id against several field candidates.
    Return the field name that yields a 200 without backend parse error.
    """
    candidates = ["dataProviders", "dataProviders.id", "repositories", "repositories.id"]
    # minimal query: provider-only with a broad year to avoid date parser issues
    for field in candidates:
        q = f'yearPublished:[2018 TO 2025] AND ({field}:{one_provider_id})'
        body = {"q": q, "limit": 1}
        try:
            _ = _post("search/works", body, retries=2)
            # if we got here without raising, field syntax is accepted (even if 0 results)
            return field
        except RuntimeError as e:
            # backend parse errors show up here; try next candidate
            continue
    raise RuntimeError("Could not detect a valid provider field (tried dataProviders, dataProviders.id, repositories, repositories.id)")

def build_query(provider_ids: List[int], provider_field: str, year_from: int = 2018, year_to: int = 2025, include_marine_terms: bool = True) -> str:
    # Join providers in OR
    prov = " OR ".join(f"{provider_field}:{pid}" for pid in provider_ids)
    year_q = f"yearPublished:[{year_from} TO {year_to}]"
    if include_marine_terms:
        return f"( {MARINE_TERMS} ) AND {year_q} AND ( {prov} )"
    else:
        return f"{year_q} AND ( {prov} )"

def scroll_works(q: str, limit: int = 100, select: Optional[List[str]] = None, max_docs: Optional[int] = None) -> list:
    """
    CORE scroll helper:
      - first call with {"scroll": "true"}
      - subsequent calls with "scrollId"
    """
    body = {"q": q, "limit": limit, "scroll": "true"}
    if select:
        body["select"] = select

    data = _post("search/works", body)
    results, total = [], 0
    sid = data.get("scrollId")
    chunk = data.get("results", []) or []
    results.extend(chunk)
    total += len(chunk)

    while sid:
        body = {"q": q, "limit": limit, "scrollId": sid}
        if select:
            body["select"] = select
        data = _post("search/works", body)
        sid = data.get("scrollId")
        chunk = data.get("results", []) or []
        if not chunk:
            break
        results.extend(chunk)
        total += len(chunk)
        if max_docs and total >= max_docs:
            break
        time.sleep(0.4)  # be polite
    return results

def scroll_works_batched(provider_ids: List[int], year_from: int = 2018, year_to: int = 2025,
                         select: Optional[List[str]] = None, batch_size: int = 20,
                         max_docs_total: Optional[int] = None, include_marine_terms: bool = True) -> list:
    """
    Split provider IDs into small OR batches to avoid boolean clause limits.
    """
    if not provider_ids:
        return []
    # detect field using the first provider id
    field = detect_provider_field(provider_ids[0])
    print(f"[info] using provider field: {field}")

    results, count = [], 0
    for i in range(0, len(provider_ids), batch_size):
        batch = provider_ids[i:i+batch_size]
        q = build_query(batch, field, year_from, year_to, include_marine_terms=include_marine_terms)
        rows = scroll_works(q, limit=100, select=select, max_docs=None)
        results.extend(rows)
        count += len(rows)
        print(f"[batch {i//batch_size}] fetched {len(rows)} (total {count})")
        if max_docs_total and count >= max_docs_total:
            break
    return results
