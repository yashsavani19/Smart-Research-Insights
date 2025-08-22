import os, json, requests, time
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("CORE_API_KEY")  # must include "Bearer ..."
HEADERS = {"Authorization": API_KEY, "Content-Type": "application/json"}
BASE = "https://api.core.ac.uk/v3/"

def _query_api(url_fragment: str, q: str, limit: int = 100, scroll: bool = False, scroll_id: str | None = None):
    body = {"q": q, "limit": limit}
    if scroll and not scroll_id: body["scroll"] = "true"
    if scroll and scroll_id:     body["scrollId"] = scroll_id
    for i in range(5):
        r = requests.post(BASE + url_fragment, headers=HEADERS, data=json.dumps(body), timeout=30)
        if r.status_code == 200:
            try:
                data = r.json()
            except Exception:
                return {"results": []}
            if "results" in data: return data
            if "message" in data:
                try: return json.loads(data["message"])
                except Exception: return {"results": []}
            return {"results": []}
        if r.status_code in (429,500,502,503,504):
            time.sleep(2**i); continue
        raise RuntimeError(f"CORE {r.status_code}: {r.text[:200]}")
    raise RuntimeError("CORE: max retries")

def list_data_providers(country_code: str) -> list[int]:
    """Return provider IDs for a 2-letter country code (e.g., 'au', 'nz')."""
    q = f"location.countryCode:{country_code.lower()}"
    out, sid = [], None
    while True:
        resp = _query_api("search/data-providers", q, limit=200, scroll=True, scroll_id=sid)
        sid = resp.get("scrollId")
        chunk = resp.get("results", [])
        if not chunk: break
        out.extend([int(h["id"]) for h in chunk if "id" in h])
    return out

def list_providers_au_nz() -> list[int]:
    # combine AU and NZ IDs
    ids = set(list_data_providers("au")) | set(list_data_providers("nz"))
    return sorted(ids)

def query_api(url_fragment, query,limit=100):
    api_endpoint = "https://api.core.ac.uk/v3/"
    query = {"q":query, "limit":limit}
    response = requests.post(f"{api_endpoint}{url_fragment}",data = json.dumps(query), headers=HEADERS)
    if response.status_code ==200:
        return response.json(), response.elapsed.total_seconds()
    else:
        print(f"Error code {response.status_code}, {response.content}")