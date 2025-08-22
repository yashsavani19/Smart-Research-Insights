# src/core_client/smoke_core.py
from client import list_providers_au_nz
from works_scroll import scroll_works_batched

SELECT = ["id","title","doi","abstract","yearPublished","publishedDate","fullTextUrl","dataProviders","institutions"]

ids = list_providers_au_nz()
print("providers:", len(ids))
assert ids, "No provider IDs returned. Check API key / network."

# Try marine terms ON, then OFF if you get 0 (to isolate the issue)
rows = scroll_works_batched(ids, year_from=2018, year_to=2025, select=SELECT, batch_size=20, max_docs_total=200, include_marine_terms=True)
print("rows:", len(rows))
for p in rows[:5]:
    print("-", p.get("title"), "| year:", p.get("yearPublished"))
