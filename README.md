# Smart-Research-Insights

Minimal scaffold to query the CORE API and expose a simple HTTP interface.

## Prerequisites

- Python 3.10+
- A CORE API key from core.ac.uk (v3). The Authorization header should be the full value returned by CORE, e.g. `Bearer XXXXX...`.

## Setup

1. Create and activate a virtual environment (optional but recommended).
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Create a `.env` file in the project root based on `.env.example`:
```
CORE_API_KEY=Bearer YOUR_CORE_API_KEY_HERE
CORE_DEFAULT_PAGE_SIZE=10
CORE_MAX_RETRIES=5
CORE_TIMEOUT_SECONDS=30
```

## Run the API server

Start the FastAPI app (Hot reload during development):
```
uvicorn app.main:app --reload
```

- Health check: `GET http://127.0.0.1:8000/health`
- Search works: `GET http://127.0.0.1:8000/search?filter=institutions.country:AU|NZ&size=5&page=1`

Interactive docs will be at `http://127.0.0.1:8000/docs`.

## CLI test script

You can also run the simple script in `src/test-coreapi.py` to fetch a page and print `id` and `title`:
```
python src/test-coreapi.py
```

## Project layout

- `app/` — FastAPI app and CORE client
- `src/` — ad-hoc scripts
- `data/raw`, `data/clean` — placeholders for ingestion/processing outputs
- `models/` — placeholders for future artifacts/checkpoints

## Next steps

- Add ingestion job to persist results to `data/raw` and paginate
- Implement cleaning/transforms to `data/clean`
- Wire a database using `psycopg2-binary` (PostgreSQL) with env-configured DSN