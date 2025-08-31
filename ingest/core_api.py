"""
CORE API v3 client for fetching research papers.
"""
import os
import time
import json
import hashlib
from typing import Dict, Any, Optional
import requests
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class CoreAPIClient:
    """Client for CORE API v3 with retry logic and logging."""
    
    def __init__(self):
        self.api_key = os.getenv("CORE_API_KEY")
        self.base_url = os.getenv("CORE_BASE_URL", "https://api.core.ac.uk/v3/search/works")
        
        if not self.api_key:
            raise ValueError("CORE_API_KEY environment variable is required")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
    
    def _make_request(self, query: Dict[str, Any], max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Make a request to CORE API with exponential backoff retry logic."""
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Making CORE API request (attempt {attempt + 1}/{max_retries})")
                
                response = self.session.post(self.base_url, json=query, timeout=30)
                
                # Log response headers for debugging
                if "X-RateLimit-Remaining" in response.headers:
                    logger.info(f"Rate limit remaining: {response.headers['X-RateLimit-Remaining']}")
                
                if "X-RateLimit-Reset" in response.headers:
                    logger.info(f"Rate limit reset: {response.headers['X-RateLimit-Reset']}")
                
                response.raise_for_status()
                
                data = response.json()
                
                # Log unknown response shapes
                if "results" not in data:
                    logger.warning(f"Unexpected response shape: {list(data.keys())}")
                
                return data
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded")
                    return None
    
    def search_works(self, query: str, page: int = 0, page_size: int = 100) -> Optional[Dict[str, Any]]:
        """
        Search for works using CORE API v3.
        
        Args:
            query: Search query string
            page: Page number (0-based)
            page_size: Number of results per page
            
        Returns:
            API response as dictionary or None if failed
        """
        
        search_query = {
            "q": query,
            "limit": page_size,
            "offset": page * page_size,
            "scroll": False
        }
        
        logger.info(f"Searching CORE API: '{query}' (page {page}, size {page_size})")
        
        response = self._make_request(search_query)
        
        if response:
            total_hits = response.get("totalHits", 0)
            results_count = len(response.get("results", []))
            logger.info(f"Received {results_count} results (total: {total_hits})")
        
        return response
    
    def build_year_language_query(self, from_year: int, to_year: int, language: str = "en") -> str:
        """
        Build a query string for year range and language.
        
        Args:
            from_year: Start year
            to_year: End year
            language: Language code (default: "en")
            
        Returns:
            Formatted query string
        """
        return f"year:[{from_year} TO {to_year}] AND language:{language}"
    
    def get_content_hash(self, title: str, abstract: str) -> str:
        """
        Generate a content hash for deduplication.
        
        Args:
            title: Document title
            abstract: Document abstract
            
        Returns:
            SHA256 hash of title and abstract
        """
        content = f"{title or ''}|{abstract or ''}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


if __name__ == "__main__":
    # Test the client
    client = CoreAPIClient()
    query = client.build_year_language_query(2021, 2022)
    response = client.search_works(query, page=0, page_size=10)
    
    if response:
        print(f"Found {response.get('totalHits', 0)} total results")
        print(f"First result: {response.get('results', [])[0].get('title', 'No title') if response.get('results') else 'No results'}")
    else:
        print("Failed to get response")
