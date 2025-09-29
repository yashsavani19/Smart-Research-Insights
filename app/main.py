from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from .core_client import CoreApiClient


app = FastAPI(title="Smart Research Insights API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/search")
def search(
    filter: Optional[str] = Query(None, description="CORE filter query, e.g., institutions.country:AU|NZ"),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
):
    client = CoreApiClient()
    payload = client.search_works(filter_query=filter, page=page, size=size)
    if not payload:
        raise HTTPException(status_code=502, detail="Failed to fetch data from CORE API")
    return payload


def get_app() -> FastAPI:
    return app


