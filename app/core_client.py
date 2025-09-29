import json
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

from .config import settings, get_auth_header


class CoreApiClient:
    def __init__(self,
                 session: Optional[requests.Session] = None,
                 max_retries: Optional[int] = None,
                 timeout_seconds: Optional[int] = None) -> None:
        self.session = session or requests.Session()
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.timeout_seconds

    def _request(self, method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        url = f"{settings.base_url}{path}"
        headers = get_auth_header()

        for attempt in range(self.max_retries):
            response = self.session.request(method, url, params=params, headers=headers, timeout=self.timeout_seconds)
            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    # Attempt to parse nested message if present
                    try:
                        payload = response.json()
                        if isinstance(payload, dict) and "message" in payload:
                            return json.loads(payload["message"])  # type: ignore[arg-type]
                    except Exception:
                        return None
            elif response.status_code in (429, 500, 502, 503, 504):
                backoff_seconds = 2 ** attempt
                time.sleep(backoff_seconds)
                continue
            else:
                return None
        return None

    def search_works(self,
                      filter_query: Optional[str] = None,
                      page: int = 1,
                      size: Optional[int] = None,
                      extra_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "page": page,
            "size": size if size is not None else settings.default_page_size,
        }
        if filter_query:
            params["filter"] = filter_query
        if extra_params:
            params.update(extra_params)

        result = self._request("GET", settings.works_search_path, params=params)
        return result or {}

    def iterate_all_results(self,
                            filter_query: Optional[str] = None,
                            size: Optional[int] = None,
                            extra_params: Optional[Dict[str, Any]] = None,
                            start_page: int = 1) -> Iterable[Dict[str, Any]]:
        page = start_page
        while True:
            payload = self.search_works(filter_query=filter_query, page=page, size=size, extra_params=extra_params)
            results: List[Dict[str, Any]] = []
            if "results" in payload and isinstance(payload["results"], list):
                results = payload["results"]
            elif isinstance(payload.get("message"), str):
                try:
                    inner = json.loads(payload["message"])  # type: ignore[index]
                    results = inner.get("results", [])  # type: ignore[assignment]
                except Exception:
                    results = []

            if not results:
                break

            for item in results:
                yield item

            page += 1


