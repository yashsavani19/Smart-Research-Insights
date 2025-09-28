import os, requests
from dotenv import load_dotenv

# Load your CORE API key
load_dotenv()
API_KEY = os.getenv("CORE_API_KEY")
if not API_KEY:
    raise SystemExit("Set CORE_API_KEY in .env as CORE_API_KEY=Bearer <your_key>")

URL = "https://api.core.ac.uk/v3/search/works"
HEADERS = {"Authorization": API_KEY}


print("Making a test request to CORE...")

r = requests.get(URL, headers=HEADERS, timeout=30)

print("\nStatus:", r.status_code)
print("\nHeaders:")
for k, v in r.headers.items():
    if "limit" in k.lower() or "rate" in k.lower():
        print(f"  {k}: {v}")

