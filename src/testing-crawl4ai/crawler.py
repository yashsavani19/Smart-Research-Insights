# # -*- coding: utf-8 -*-
# """
# AUT Research Crawler (Smart-Research-Insights)
# ----------------------------------------------
# Style: "Discover → Rank → Crawl → Extract → Save"
# Target: openrepository.aut.ac.nz (DSpace)
# Run:   python aut_research_crawler.py
# """

# import asyncio
# import csv
# import re
# import sys
# from dataclasses import dataclass
# from datetime import datetime
# from pathlib import Path
# from typing import List, Dict, Optional
# from urllib.parse import urljoin

# # Crawl4AI (browser + crawler + URL seeder)
# from crawl4ai import (
#     AsyncUrlSeeder,
#     SeedingConfig,
#     AsyncLogger,
#     AsyncWebCrawler,
#     BrowserConfig,
#     CrawlerRunConfig,
# )
# from crawl4ai import DefaultMarkdownGenerator
# from crawl4ai import PruningContentFilter

# # Simple HTTP fallback for sitemap parsing (if seeder returns too few)
# import requests
# from bs4 import BeautifulSoup


# # -----------------------------
# # 1) Config & Query containers
# # -----------------------------
# @dataclass
# class ResearchConfig:
#     domain: str = "sciencedirect.com"
#     base_url: str = "https://www.sciencedirect.com/"
#     # discovery
#     max_urls_discovery: int = 500
#     top_k_urls: int = 80            # keep the best N after ranking
#     score_threshold: float = 0.25   # lower if you want more candidates
#     scoring_method: str = "bm25"    # Crawl4AI seeder ranking
#     extract_head_metadata: bool = True
#     live_check: bool = True
#     force_refresh: bool = False
#     # crawling
#     max_urls_to_crawl: int = 40     # final crawl budget
#     max_concurrent_crawls: int = 4
#     headless: bool = True
#     verbose: bool = True
#     timeout_ms: int = 30000
#     # output
#     output_dir: Path = Path("research_results")
#     output_csv: str = "aut_papers.csv"

# @dataclass
# class ResearchQuery:
#     text: str                     # e.g. "marine renewable energy"
#     keywords: List[str]           # e.g. ["marine","ocean","aquaculture","renewable","energy"]


# # -------------------------------------------------
# # 2) URL Discovery: Crawl4AI URL Seeder (preferred)
# # -------------------------------------------------
# async def discover_urls_with_seeder(cfg: ResearchConfig, rq: ResearchQuery) -> List[Dict]:
#     """
#     Use Crawl4AI's AsyncUrlSeeder to fetch and rank candidate URLs.
#     Sources: sitemap + CommonCrawl. Already returns relevance scores (BM25).
#     """
#     print(f"\n🔎 Discovering URLs on {cfg.domain} for query: '{rq.text}'")
#     async with AsyncUrlSeeder(logger=AsyncLogger(verbose=cfg.verbose)) as seeder:
#         seed_cfg = SeedingConfig(
#             source="sitemap+cc",
#             query=rq.text,
#             scoring_method=cfg.scoring_method,
#             score_threshold=cfg.score_threshold,
#             extract_head=cfg.extract_head_metadata,
#             live_check=cfg.live_check,
#             force=cfg.force_refresh,
#             max_urls=cfg.max_urls_discovery,
#         )
#         urls = await seeder.urls(cfg.domain, seed_cfg)

#     # # Keep only handle pages (DSpace item pages)
#     # urls = [u for u in urls if "/items/" in u.get("url","")]
#     # urls = urls[:cfg.top_k_urls]
#     # print(f"✅ Discovered {len(urls)} candidate URLs (after handle/* filter)")
#     return urls


# # -----------------------------------------------------------
# # 3) Fallback discovery via sitemap (in case seeder is sparse)
# # -----------------------------------------------------------
# def discover_urls_from_sitemap(cfg: ResearchConfig, rq: ResearchQuery) -> List[Dict]:
#     """
#     Parse the site's sitemap(s) to collect /handle/ links and score them
#     with a simple keyword heuristic. This is a lightweight fallback.
#     """
#     print("ℹ️  Using sitemap fallback discovery...")
#     sitemap_index_urls = [
#         urljoin(cfg.base_url, "sitemap_index.xml"),
#         urljoin(cfg.base_url, "sitemap_index.html"),
#         urljoin(cfg.base_url, "sitemap.xml"),
#     ]

#     found = set()
#     for sm in sitemap_index_urls:
#         try:
#             r = requests.get(sm, timeout=15)
#             if r.status_code != 200:
#                 continue
#             soup = BeautifulSoup(r.text, "xml") if sm.endswith(".xml") else BeautifulSoup(r.text, "html.parser")
#             # collect <loc> entries if XML; else collect hrefs
#             if sm.endswith(".xml"):
#                 locs = [loc.text.strip() for loc in soup.find_all("loc")]
#             else:
#                 locs = [a.get("href","") for a in soup.find_all("a", href=True)]
#             for loc in locs:
#                 if "/items/" in loc:
#                     found.add(loc)
#         except Exception:
#             pass

#     # score by keyword presence in URL (very rough); higher if many keyword hits
#     def score(url: str) -> float:
#         u = url.lower()
#         return sum(1 for k in rq.keywords if k in u) / max(1, len(rq.keywords))

#     ranked = sorted([{"url": u, "relevance_score": score(u)} for u in found],
#                     key=lambda x: x["relevance_score"], reverse=True)
#     ranked = [u for u in ranked if u["relevance_score"] >= 0.1][:cfg.top_k_urls]
#     print(f"✅ Sitemap fallback found {len(ranked)} candidate URLs")
#     return ranked


# # ---------------------------------------
# # 4) Crawl: Batch-crawl the top N URLs
# # ---------------------------------------
# async def crawl_selected_urls(top_urls: List[Dict], cfg: ResearchConfig) -> List[Dict]:
#     """
#     Crawl only the selected URLs (batch crawl). No deep crawl here.
#     We generate clean Markdown and strip UI noise.
#     """
#     url_list = [u["url"] for u in top_urls][:cfg.max_urls_to_crawl]
#     if not url_list:
#         print("❌ No URLs to crawl")
#         return []

#     print(f"\n🕷️ Crawling {len(url_list)} URLs...")

#     md_gen = DefaultMarkdownGenerator(
#         content_filter=PruningContentFilter(
#             threshold=0.48, threshold_type="dynamic", min_word_threshold=10
#         )
#     )

#     run_cfg = CrawlerRunConfig(
#         markdown_generator=md_gen,
#         exclude_external_links=True,
#         excluded_tags=["nav", "header", "footer", "aside"],
#         timeout=cfg.timeout_ms,
#         verbose=cfg.verbose,
#     )

#     async with AsyncWebCrawler(config=BrowserConfig(headless=cfg.headless, verbose=cfg.verbose)) as crawler:
#         results = await crawler.arun_many(
#             url_list,
#             config=run_cfg,
#             max_concurrent=cfg.max_concurrent_crawls
#         )

#     crawled = []
#     for url, res in zip(url_list, results):
#         if getattr(res, "success", False):
#             markdown = getattr(res.markdown, "fit_markdown", None) or getattr(res.markdown, "raw_markdown", "")
#             crawled.append({
#                 "url": url,
#                 "title": res.metadata.get("title") or "",
#                 "markdown": markdown,
#                 "metadata": res.metadata
#             })
#             print(f"  ✓ {url}")
#         else:
#             err = getattr(res, "error", "unknown")
#             print(f"  ✗ {url} — {err}")
#     print(f"✅ Successfully crawled {len(crawled)} pages")
#     return crawled


# # ------------------------------------------------------
# # 5) Extract: title + abstract (DSpace-friendly parser)
# # ------------------------------------------------------
# def extract_title_and_abstract(markdown: str) -> Dict[str, Optional[str]]:
#     """
#     DSpace item pages usually expose:
#       - a page <title> (we keep Crawl4AI's metadata elsewhere)
#       - an 'Abstract' section in the body
#     We'll look for 'Abstract' heading or 'Abstract:' label.
#     """
#     if not markdown:
#         return {"title_guess": None, "abstract": None}

#     # Title guess: first H1/H2 line in markdown
#     title_guess = None
#     for line in markdown.splitlines():
#         if line.startswith("# "):
#             title_guess = line[2:].strip()
#             break
#         if line.startswith("## "):
#             title_guess = line[3:].strip()
#             break

#     # Abstract extraction:
#     # 1) Look for a heading named 'Abstract'
#     abstract = None
#     m = re.search(r"(?im)^\s*#+\s*abstract\s*$([\s\S]{0,1200})", markdown)
#     if m:
#         # take paragraph(s) until next heading
#         block = m.group(1)
#         block = re.split(r"(?m)^\s*#\s", block)[0]
#         abstract = block.strip()

#     # 2) Or look for 'Abstract:' label
#     if not abstract:
#         m2 = re.search(r"(?is)abstract\s*:\s*(.{100,3000})", markdown)
#         if m2:
#             abstract = m2.group(1)
#             # stop at next strong delimiter or heading
#             abstract = re.split(r"(?m)^\s*#|^\s*[-=]{3,}|^\s*$", abstract)[0].strip()

#     # cleanup
#     if abstract:
#         abstract = re.sub(r"\s+", " ", abstract).strip()

#     return {"title_guess": title_guess, "abstract": abstract}


# # --------------------------
# # 6) Save to CSV (simple)
# # --------------------------
# def save_to_csv(rows: List[Dict], cfg: ResearchConfig):
#     cfg.output_dir.mkdir(parents=True, exist_ok=True)
#     out_path = cfg.output_dir / cfg.output_csv
#     with open(out_path, "w", newline="", encoding="utf-8") as f:
#         w = csv.writer(f)
#         w.writerow(["title", "abstract", "url", "crawled_at"])
#         for r in rows:
#             w.writerow([r.get("title") or r.get("title_guess") or "",
#                         r.get("abstract") or "",
#                         r.get("url"),
#                         datetime.utcnow().isoformat()])
#     print(f"💾 Saved {len(rows)} rows → {out_path.resolve()}")


# # --------------------------
# # 7) Orchestrate pipeline
# # --------------------------
# async def run_pipeline(rq: ResearchQuery, cfg: ResearchConfig):
#     # 1) Discover
#     discovered = await discover_urls_with_seeder(cfg, rq)
#     if len(discovered) < 10:
#         # fallback if needed
#         discovered = discover_urls_from_sitemap(cfg, rq)

#     if not discovered:
#         print("❌ No candidates found. Try adjusting keywords/thresholds.")
#         return

#     # 2) Crawl
#     crawled = await crawl_selected_urls(discovered, cfg)
#     if not crawled:
#         print("❌ Nothing crawled.")
#         return

#     # 3) Extract
#     rows = []
#     for rec in crawled:
#         parsed = extract_title_and_abstract(rec["markdown"])
#         rows.append({
#             "title": rec["title"] or parsed["title_guess"],
#             "abstract": parsed["abstract"],
#             "url": rec["url"]
#         })

#     # basic filter: keep entries that actually have an abstract
#     rows = [r for r in rows if r["abstract"] and len(r["abstract"]) > 80]
#     print(f"🧹 Kept {len(rows)} records with usable abstracts")

#     # 4) Save
#     save_to_csv(rows, cfg)


# # --------------------------
# # 8) Entry point
# # --------------------------
# if __name__ == "__main__":
#     # Example query — tune keywords to your theme
#     rq = ResearchQuery(
#         text="marine renewable energy OR aquaculture robotics OR ocean engineering",
#         keywords=["marine", "ocean", "aquaculture", "renewable", "energy", "robotics", "sensors", "autonomous"]
#     )
#     cfg = ResearchConfig()

#     # On Windows, ensure the right event loop (for Playwright subprocess)
#     if sys.platform.startswith("win"):
#         import asyncio
#         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#     asyncio.run(run_pipeline(rq, cfg))


# -*- coding: utf-8 -*-
"""
Fetch AU/NZ marine-tech research from OpenAlex for the last 5 years.
Outputs: CSV + JSONL with title, abstract, DOI, URL, date, institutions, concepts.

Run:
    python get_openalex_5y.py
"""

import csv
import json
import time
import datetime as dt
from urllib.parse import urlencode
import requests

# ---------------------------------------------------------
# CONFIG — tweak as you like
# ---------------------------------------------------------

# A single broad query that covers your marine/ocean anchors + tech themes.
QUERY = (
    '('
    'marine OR ocean OR offshore OR maritime OR naval OR ship OR aquaculture'
    ') AND ('
    # Autonomy / AI / inspection
    '"autonomous underwater vehicle" OR AUV OR ROV OR ASV OR USV OR autonomous OR "path planning" OR SLAM OR "computer vision" OR "defect detection" OR "predictive maintenance" OR "condition-based maintenance" OR CBM OR "digital twin" OR "data fusion" OR "edge computing" OR "multi-sensor fusion" OR "time-series anomaly detection" OR "change detection"'
    ' OR '
    # Sensors / comms
    'sonar OR "acoustic sensing" OR "ultrasonic" OR "multibeam echosounder" OR "sidescan sonar" OR "underwater acoustic communication" OR "optical modem" OR "blue-green laser" OR "acoustic modem"'
    ' OR '
    # Energy / sustainability
    '"marine renewable energy" OR "wave energy" OR "wave energy converter" OR "tidal turbine" OR "offshore wind" OR "floating wind" OR "battery thermal management" OR "energy efficiency" OR "air lubrication" OR "life cycle assessment"'
    ' OR '
    # Materials / coatings
    '"corrosion resistant" OR antifouling OR biofouling OR "marine coatings" OR "cathodic protection" OR CFRP OR GFRP'
    ' OR '
    # Data / navigation
    '"AIS analytics" OR "vessel trajectory" OR "trajectory prediction"'
    ')'
)

# AU/NZ focus
COUNTRY_FILTER = "AU|NZ"    # filter by author institutions’ country (Australia/New Zealand)

# Time window: last 5 years
DAYS_BACK = 5 * 365

# OpenAlex page size & politeness
PER_PAGE = 200              # OpenAlex max per_page=200
PAUSE_SEC = 0.25            # short delay between pages

# Output files
OUTPUT_CSV = "openalex_papers_5y.csv"
OUTPUT_JSONL = "openalex_papers_5y.jsonl"

# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def since_date(days_back: int) -> str:
    return (dt.date.today() - dt.timedelta(days=days_back)).isoformat()

def reconstruct_openalex_abstract(inv_idx: dict) -> str:
    """Rebuild plain-text abstract from OpenAlex's inverted index, if needed."""
    pairs = [(pos, token) for token, positions in inv_idx.items() for pos in positions]
    pairs.sort(key=lambda x: x[0])
    return " ".join(tok for _, tok in pairs)

def normalize_work(w: dict) -> dict:
    """
    Convert an OpenAlex 'work' result to a consistent row for CSV/JSONL.
    """
    abstract = w.get("abstract") or ""
    if not abstract and w.get("abstract_inverted_index"):
        abstract = reconstruct_openalex_abstract(w["abstract_inverted_index"])

    url = (w.get("primary_location") or {}).get("landing_page_url") or w.get("id")
    pub_date = (w.get("publication_date") or "")[:10] or None

    return {
        "title": w.get("title") or "",
        "abstract": abstract or "",
        "doi": w.get("doi"),
        "url": url,
        "source": "openalex",
        "published_date": pub_date,
        "institutions": w.get("authorships") or [],
        "concepts": w.get("concepts") or [],
    }

# ---------------------------------------------------------
# Main fetch loop
# ---------------------------------------------------------

def fetch_openalex_5y():
    base = "https://api.openalex.org/works"

    filters = [
        f'from_publication_date:{since_date(DAYS_BACK)}',
        'has_abstract:true',
        f'institutions.country_code:{COUNTRY_FILTER}',
    ]

    params = {
        "search": QUERY,
        "filter": ",".join(filters),
        "per_page": PER_PAGE,
        "cursor": "*",
        # "sort": "publication_date:desc",  # optional
    }

    print("\n=== OpenAlex 5-year fetch ===")
    print("Query:\n ", QUERY)
    print("Filters:\n ", filters)
    print("Output:\n ", OUTPUT_CSV, "and", OUTPUT_JSONL, "\n")

    total = 0

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_csv, \
         open(OUTPUT_JSONL, "w", encoding="utf-8") as f_jsonl:
        writer = csv.writer(f_csv)
        writer.writerow([
            "title", "abstract", "doi", "url",
            "source", "published_date", "institutions", "concepts"
        ])

        while True:
            url = f"{base}?{urlencode(params)}"
            r = requests.get(url, timeout=45)
            r.raise_for_status()
            data = r.json()

            results = data.get("results", [])
            if not results:
                break

            for w in results:
                row = normalize_work(w)

                writer.writerow([
                    row["title"], row["abstract"], row["doi"], row["url"],
                    row["source"], row["published_date"],
                    json.dumps(row["institutions"], ensure_ascii=False),
                    json.dumps(row["concepts"], ensure_ascii=False),
                ])
                f_jsonl.write(json.dumps(row, ensure_ascii=False) + "\n")
                total += 1

            print(f"  +{len(results)} (total: {total})")
            next_cursor = (data.get("meta") or {}).get("next_cursor")
            if not next_cursor:
                break

            params["cursor"] = next_cursor
            time.sleep(PAUSE_SEC)

    print(f"\n✅ Done. Wrote {total} rows → {OUTPUT_CSV} and {OUTPUT_JSONL}")
    return total

# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    fetch_openalex_5y()
