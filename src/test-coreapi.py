import os, time, json, requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CORE_API_KEY")
URL     = "https://api.core.ac.uk/v3/search/works"
headers = {"Authorization": API_KEY}

def fetch_page(params):
    for attempt in range(5):
        r = requests.get(URL, params=params, headers=headers)
        if r.status_code == 200:
            return r.json()
        elif r.status_code in (429, 500):
            # Too many requests or server error: back off and retry
            backoff = 2 ** attempt
            print(f"{r.status_code}—retrying in {backoff}s…")
            time.sleep(backoff)
        else:
            # Other errors: bail out
            print(f"Unexpected status {r.status_code}: {r.text}")
            return None
    print("Max retries reached, giving up on this page.")
    return None

params = {"filter":"institutions.country:AU|NZ","size":5,"page":1}
resp = fetch_page(params)
if not resp:
    raise SystemExit("Failed to fetch data.")
# CORE sometimes wraps failures under 'message'
if "results" not in resp:
    # Try to pull actual JSON inside the 'message' string
    raw = resp.get("message")
    try:
        inner = json.loads(raw)
        data = inner.get("results", [])
    except Exception:
        data = []
else:
    data = resp["results"]

for paper in data:
    print(paper.get("id"), paper.get("title"))
