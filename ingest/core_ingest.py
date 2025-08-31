"""
CORE API ingestion script for fetching and normalizing research papers.
"""
import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from tqdm import tqdm
from loguru import logger
import yaml

from core_api import CoreAPIClient


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        logger.warning("config.yaml not found, using defaults")
        return {
            "page_size": 100,
            "max_pages": 200
        }


def normalize_authors(authors: List[Dict[str, Any]]) -> str:
    """Normalize authors list to comma-separated string."""
    if not authors:
        return ""
    
    author_names = []
    for author in authors:
        if isinstance(author, dict):
            # Try different possible author name fields
            name = (author.get("name") or 
                   author.get("fullName") or 
                   f"{author.get('firstName', '')} {author.get('lastName', '')}".strip())
            if name:
                author_names.append(name)
        elif isinstance(author, str):
            author_names.append(author)
    
    return ", ".join(author_names)


def normalize_urls(record: Dict[str, Any]) -> tuple[str, str]:
    """Extract and normalize URL fields."""
    url = ""
    pdf_url = ""
    
    # Try to get main URL
    if "downloadUrl" in record and record["downloadUrl"]:
        url = record["downloadUrl"]
    elif "sourceFulltextUrl" in record and record["sourceFulltextUrl"]:
        url = record["sourceFulltextUrl"]
    elif "urls" in record and record["urls"]:
        # Take first URL if multiple exist
        if isinstance(record["urls"], list) and record["urls"]:
            url = record["urls"][0]
        elif isinstance(record["urls"], str):
            url = record["urls"]
    
    # Try to get PDF URL
    if "pdfUrl" in record and record["pdfUrl"]:
        pdf_url = record["pdfUrl"]
    elif "downloadUrl" in record and record["downloadUrl"] and record["downloadUrl"].endswith('.pdf'):
        pdf_url = record["downloadUrl"]
    
    return url, pdf_url


def normalize_record(record: Dict[str, Any], client: CoreAPIClient) -> Dict[str, Any]:
    """Normalize a CORE API record to our schema."""
    
    # Extract basic fields
    core_id = str(record.get("id", ""))
    doi = record.get("doi", "")
    title = record.get("title", "")
    abstract = record.get("abstract", "")
    full_text = record.get("fullText", "")
    venue = record.get("venue", "")
    year = record.get("year")
    lang = record.get("language", "")
    
    # Normalize authors
    authors = normalize_authors(record.get("authors", []))
    
    # Normalize URLs
    url, pdf_url = normalize_urls(record)
    
    # Generate content hash
    content_hash = client.get_content_hash(title, abstract)
    
    return {
        "core_id": core_id,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "full_text": full_text,
        "authors": authors,
        "venue": venue,
        "year": year,
        "lang": lang,
        "url": url,
        "pdf_url": pdf_url,
        "raw_json": record,
        "content_hash": content_hash
    }


def ingest_core_papers(
    from_year: int,
    to_year: int,
    lang: str = "en",
    limit: Optional[int] = None,
    page_size: int = 100,
    max_pages: int = 200,
    out_base: str = "data"
) -> None:
    """
    Ingest papers from CORE API and save to files.
    
    Args:
        from_year: Start year
        to_year: End year
        lang: Language code
        limit: Maximum number of papers to fetch (None for all)
        page_size: Results per page
        max_pages: Maximum pages to fetch
        out_base: Base directory for output files
    """
    
    # Create output directories
    raw_dir = Path(out_base) / "raw"
    clean_dir = Path(out_base) / "clean"
    raw_dir.mkdir(parents=True, exist_ok=True)
    clean_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize API client
    client = CoreAPIClient()
    
    # Build query
    query = client.build_year_language_query(from_year, to_year, lang)
    logger.info(f"Query: {query}")
    
    # Prepare output files
    raw_file = raw_dir / f"core_{from_year}_{to_year}_{lang}.jsonl"
    clean_file = clean_dir / f"{from_year}_{to_year}_{lang}.parquet"
    
    all_records = []
    total_fetched = 0
    page = 0
    
    logger.info(f"Starting ingestion: {from_year}-{to_year}, language: {lang}")
    
    with open(raw_file, 'w', encoding='utf-8') as raw_f:
        with tqdm(desc="Fetching papers", unit="page") as pbar:
            while page < max_pages:
                # Check limit
                if limit and total_fetched >= limit:
                    logger.info(f"Reached limit of {limit} papers")
                    break
                
                # Fetch page
                response = client.search_works(query, page=page, page_size=page_size)
                
                if not response:
                    logger.error(f"Failed to fetch page {page}")
                    break
                
                results = response.get("results", [])
                if not results:
                    logger.info(f"No more results at page {page}")
                    break
                
                # Process results
                for record in results:
                    # Check limit
                    if limit and total_fetched >= limit:
                        break
                    
                    # Save raw JSON
                    raw_f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    
                    # Normalize and collect
                    normalized = normalize_record(record, client)
                    all_records.append(normalized)
                    total_fetched += 1
                
                pbar.update(1)
                pbar.set_postfix({"total": total_fetched})
                
                page += 1
                
                # Check if we've reached the end
                total_hits = response.get("totalHits", 0)
                if total_fetched >= total_hits:
                    logger.info(f"Reached end of results ({total_hits} total)")
                    break
    
    # Save normalized data
    if all_records:
        df = pd.DataFrame(all_records)
        df.to_parquet(clean_file, index=False)
        logger.info(f"Saved {len(df)} records to {clean_file}")
        
        # Log summary
        logger.info(f"Ingestion complete:")
        logger.info(f"  Raw JSONL: {raw_file}")
        logger.info(f"  Clean Parquet: {clean_file}")
        logger.info(f"  Total papers: {len(df)}")
        logger.info(f"  Years: {df['year'].min()}-{df['year'].max()}")
        logger.info(f"  Venues: {df['venue'].nunique()}")
    else:
        logger.warning("No records were fetched")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Ingest papers from CORE API")
    parser.add_argument("--from_year", type=int, required=True, help="Start year")
    parser.add_argument("--to_year", type=int, required=True, help="End year")
    parser.add_argument("--lang", type=str, default="en", help="Language code")
    parser.add_argument("--limit", type=int, help="Maximum papers to fetch")
    parser.add_argument("--page_size", type=int, help="Results per page")
    parser.add_argument("--max_pages", type=int, help="Maximum pages to fetch")
    parser.add_argument("--out_base", type=str, default="data", help="Output base directory")
    
    args = parser.parse_args()
    
    # Load config for defaults
    config = load_config()
    
    # Use args or config defaults
    page_size = args.page_size or config.get("page_size", 100)
    max_pages = args.max_pages or config.get("max_pages", 200)
    
    ingest_core_papers(
        from_year=args.from_year,
        to_year=args.to_year,
        lang=args.lang,
        limit=args.limit,
        page_size=page_size,
        max_pages=max_pages,
        out_base=args.out_base
    )


if __name__ == "__main__":
    main()
