"""
End-to-end pipeline runner for BERTopic CORE online MVP.
"""
import argparse
import os
import sys
from pathlib import Path
from typing import Optional
import pandas as pd
from loguru import logger
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from ingest.core_ingest import ingest_core_papers
from pipelines.pipeline_online import OnlineBERTopicPipeline
from pipelines.db_writer import DatabaseWriter


def load_config() -> dict:
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


def create_topic_trends(assignments_df: pd.DataFrame, documents_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create topic trends from assignments and documents.
    
    Args:
        assignments_df: DataFrame with topic assignments
        documents_df: DataFrame with documents
        
    Returns:
        DataFrame with topic trends
    """
    if assignments_df.empty or documents_df.empty:
        return pd.DataFrame()
    
    # Merge assignments with documents to get year/month
    merged = assignments_df.merge(
        documents_df[['doc_id', 'year']].reset_index().rename(columns={'index': 'doc_id'}),
        on='doc_id',
        how='left'
    )
    
    # Add month (default to 1 if not available)
    merged['month'] = 1
    
    # Group by topic, year, month and count documents
    trends = merged.groupby(['topic_id', 'year', 'month']).size().reset_index(name='doc_count')
    
    return trends


def run_end_to_end(
    from_year: int,
    to_year: int,
    lang: str = "en",
    limit: Optional[int] = None,
    init_if_missing: bool = True,
    skip_db: bool = False
) -> None:
    """
    Run the complete end-to-end pipeline.
    
    Args:
        from_year: Start year
        to_year: End year
        lang: Language code
        limit: Maximum papers to fetch
        init_if_missing: Initialize model if it doesn't exist
        skip_db: Skip database operations
    """
    logger.info(f"Starting end-to-end pipeline: {from_year}-{to_year}, language: {lang}")
    
    # Load config
    config = load_config()
    
    # Step 1: Ingest papers from CORE API
    logger.info("Step 1: Ingesting papers from CORE API")
    try:
        ingest_core_papers(
            from_year=from_year,
            to_year=to_year,
            lang=lang,
            limit=limit,
            page_size=config.get("page_size", 100),
            max_pages=config.get("max_pages", 200)
        )
    except Exception as e:
        logger.error(f"Failed to ingest papers: {e}")
        return
    
    # Check if ingestion created files
    clean_file = Path(f"data/clean/{from_year}_{to_year}_{lang}.parquet")
    if not clean_file.exists():
        logger.error(f"Clean data file not found: {clean_file}")
        return
    
    # Step 2: Initialize or update BERTopic model
    logger.info("Step 2: Processing BERTopic model")
    pipeline = OnlineBERTopicPipeline(config)
    
    model_path = Path("models/artifacts/bertopic_light")
    if not model_path.exists() and init_if_missing:
        logger.info("Initializing new BERTopic model")
        try:
            pipeline.init_model(str(clean_file))
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            return
    elif model_path.exists():
        logger.info("Updating existing BERTopic model")
        try:
            pipeline.update_model(str(clean_file))
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
            return
    else:
        logger.error("Model not found and init_if_missing=False")
        return
    
    # Step 3: Write to database (if enabled)
    if not skip_db:
        logger.info("Step 3: Writing to database")
        try:
            # Initialize database writer
            db_writer = DatabaseWriter()
            
            if not db_writer.test_connection():
                logger.error("Database connection failed")
                return
            
            # Load documents
            documents_df = pd.read_parquet(clean_file)
            logger.info(f"Loaded {len(documents_df)} documents")
            
            # Upsert documents
            docs_inserted = db_writer.upsert_documents(documents_df)
            logger.info(f"Documents inserted/updated: {docs_inserted}")
            
            # Get topic summary
            topic_summary = pipeline.get_topic_summary()
            logger.info(f"Topic summary: {len(topic_summary)} topics")
            
            # Prepare topic data for database
            topics_df = pd.DataFrame({
                'topic_id': topic_summary['Topic'],
                'label': topic_summary['Name'],
                'top_terms': topic_summary['Name'],  # Use Name as top_terms for now
                'size': topic_summary['Count']
            })
            
            # Upsert topics
            topics_inserted = db_writer.upsert_topics(topics_df)
            logger.info(f"Topics inserted/updated: {topics_inserted}")
            
            # Get topic terms
            topic_terms_df = pipeline.get_topic_terms()
            if not topic_terms_df.empty:
                terms_inserted = db_writer.upsert_topic_terms(topic_terms_df)
                logger.info(f"Topic terms inserted/updated: {terms_inserted}")
            
            # Get topic assignments
            assignments_df = pipeline.get_topic_assignments(documents_df)
            if not assignments_df.empty:
                # Get document ID mapping
                core_ids = documents_df['core_id'].tolist()
                doc_id_mapping = db_writer.get_document_id_mapping(core_ids)
                
                # Create reverse mapping from DataFrame index to database ID
                reverse_mapping = {}
                for i, core_id in enumerate(core_ids):
                    if core_id in doc_id_mapping:
                        reverse_mapping[i] = doc_id_mapping[core_id]
                
                assignments_inserted = db_writer.upsert_topic_assignments(assignments_df, reverse_mapping)
                logger.info(f"Topic assignments inserted/updated: {assignments_inserted}")
                
                # Create and upsert topic trends
                trends_df = create_topic_trends(assignments_df, documents_df)
                if not trends_df.empty:
                    trends_inserted = db_writer.upsert_topic_trends(trends_df)
                    logger.info(f"Topic trends inserted/updated: {trends_inserted}")
            
            # Print final table counts
            counts = db_writer.get_table_counts()
            logger.info("Final table counts:")
            for table, count in counts.items():
                logger.info(f"  {table}: {count}")
                
        except Exception as e:
            logger.error(f"Failed to write to database: {e}")
            if not skip_db:
                return
    else:
        logger.info("Skipping database operations")
    
    logger.info("End-to-end pipeline completed successfully!")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="End-to-end BERTopic CORE pipeline")
    parser.add_argument("--from_year", type=int, required=True, help="Start year")
    parser.add_argument("--to_year", type=int, required=True, help="End year")
    parser.add_argument("--lang", type=str, default="en", help="Language code")
    parser.add_argument("--limit", type=int, help="Maximum papers to fetch")
    parser.add_argument("--init_if_missing", action="store_true", help="Initialize model if missing")
    parser.add_argument("--skip_db", action="store_true", help="Skip database operations")
    
    args = parser.parse_args()
    
    run_end_to_end(
        from_year=args.from_year,
        to_year=args.to_year,
        lang=args.lang,
        limit=args.limit,
        init_if_missing=args.init_if_missing,
        skip_db=args.skip_db
    )


if __name__ == "__main__":
    main()
