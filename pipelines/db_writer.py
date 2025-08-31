"""
Database writer for BERTopic CORE online MVP.
"""
import os
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Text, DateTime, Float, BigInteger, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


class DatabaseWriter:
    """Database writer for PostgreSQL with batch operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.engine = create_engine(self.database_url)
        self.metadata = MetaData()
        
        # Define table schemas
        self._define_tables()
    
    def _define_tables(self):
        """Define table schemas for SQLAlchemy."""
        self.documents = Table(
            'documents', self.metadata,
            Column('id', BigInteger, primary_key=True, autoincrement=True),
            Column('core_id', String, unique=True),
            Column('doi', String),
            Column('title', Text),
            Column('abstract', Text),
            Column('full_text', Text),
            Column('authors', Text),
            Column('venue', String),
            Column('year', Integer),
            Column('lang', String),
            Column('url', String),
            Column('pdf_url', String),
            Column('raw_json', JSONB),
            Column('content_hash', String),
            Column('created_at', DateTime)
        )
        
        self.topics = Table(
            'topics', self.metadata,
            Column('topic_id', Integer, primary_key=True),
            Column('label', Text),
            Column('top_terms', Text),
            Column('size', Integer),
            Column('updated_at', DateTime)
        )
        
        self.topic_terms = Table(
            'topic_terms', self.metadata,
            Column('topic_id', Integer, primary_key=True),
            Column('term', String, primary_key=True),
            Column('weight', Float)
        )
        
        self.topic_assignments = Table(
            'topic_assignments', self.metadata,
            Column('doc_id', BigInteger, primary_key=True),
            Column('topic_id', Integer, primary_key=True),
            Column('probability', Float),
            Column('assigned_at', DateTime)
        )
        
        self.topic_trends = Table(
            'topic_trends', self.metadata,
            Column('topic_id', Integer, primary_key=True),
            Column('year', Integer, primary_key=True),
            Column('month', Integer, primary_key=True),
            Column('doc_count', Integer)
        )
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def upsert_documents(self, df: pd.DataFrame) -> int:
        """
        Upsert documents to database.
        
        Args:
            df: DataFrame with document data
            
        Returns:
            Number of documents inserted/updated
        """
        if df.empty:
            logger.warning("No documents to upsert")
            return 0
        
        # Prepare data for insertion
        documents_data = []
        for _, row in df.iterrows():
            doc_data = {
                'core_id': row.get('core_id'),
                'doi': row.get('doi'),
                'title': row.get('title'),
                'abstract': row.get('abstract'),
                'full_text': row.get('full_text'),
                'authors': row.get('authors'),
                'venue': row.get('venue'),
                'year': row.get('year'),
                'lang': row.get('lang'),
                'url': row.get('url'),
                'pdf_url': row.get('pdf_url'),
                'raw_json': row.get('raw_json'),
                'content_hash': row.get('content_hash')
            }
            documents_data.append(doc_data)
        
        # Batch insert with conflict resolution
        try:
            with self.engine.connect() as conn:
                # Use ON CONFLICT DO UPDATE for upsert
                stmt = text("""
                    INSERT INTO documents (core_id, doi, title, abstract, full_text, authors, venue, year, lang, url, pdf_url, raw_json, content_hash)
                    VALUES (:core_id, :doi, :title, :abstract, :full_text, :authors, :venue, :year, :lang, :url, :pdf_url, :raw_json, :content_hash)
                    ON CONFLICT (core_id) DO UPDATE SET
                        doi = EXCLUDED.doi,
                        title = EXCLUDED.title,
                        abstract = EXCLUDED.abstract,
                        full_text = EXCLUDED.full_text,
                        authors = EXCLUDED.authors,
                        venue = EXCLUDED.venue,
                        year = EXCLUDED.year,
                        lang = EXCLUDED.lang,
                        url = EXCLUDED.url,
                        pdf_url = EXCLUDED.pdf_url,
                        raw_json = EXCLUDED.raw_json,
                        content_hash = EXCLUDED.content_hash
                """)
                
                result = conn.execute(stmt, documents_data)
                conn.commit()
                
                logger.info(f"Upserted {len(documents_data)} documents")
                return len(documents_data)
                
        except SQLAlchemyError as e:
            logger.error(f"Error upserting documents: {e}")
            return 0
    
    def upsert_topics(self, df: pd.DataFrame) -> int:
        """
        Upsert topics to database.
        
        Args:
            df: DataFrame with topic data (columns: topic_id, label, top_terms, size)
            
        Returns:
            Number of topics inserted/updated
        """
        if df.empty:
            logger.warning("No topics to upsert")
            return 0
        
        # Prepare data for insertion
        topics_data = []
        for _, row in df.iterrows():
            topic_data = {
                'topic_id': int(row['topic_id']),
                'label': row.get('label', ''),
                'top_terms': row.get('top_terms', ''),
                'size': int(row.get('size', 0))
            }
            topics_data.append(topic_data)
        
        try:
            with self.engine.connect() as conn:
                stmt = text("""
                    INSERT INTO topics (topic_id, label, top_terms, size, updated_at)
                    VALUES (:topic_id, :label, :top_terms, :size, NOW())
                    ON CONFLICT (topic_id) DO UPDATE SET
                        label = EXCLUDED.label,
                        top_terms = EXCLUDED.top_terms,
                        size = EXCLUDED.size,
                        updated_at = NOW()
                """)
                
                result = conn.execute(stmt, topics_data)
                conn.commit()
                
                logger.info(f"Upserted {len(topics_data)} topics")
                return len(topics_data)
                
        except SQLAlchemyError as e:
            logger.error(f"Error upserting topics: {e}")
            return 0
    
    def upsert_topic_terms(self, df: pd.DataFrame) -> int:
        """
        Upsert topic terms to database.
        
        Args:
            df: DataFrame with topic terms data (columns: topic_id, term, weight)
            
        Returns:
            Number of topic terms inserted/updated
        """
        if df.empty:
            logger.warning("No topic terms to upsert")
            return 0
        
        # Prepare data for insertion
        terms_data = []
        for _, row in df.iterrows():
            term_data = {
                'topic_id': int(row['topic_id']),
                'term': row['term'],
                'weight': float(row['weight'])
            }
            terms_data.append(term_data)
        
        try:
            with self.engine.connect() as conn:
                stmt = text("""
                    INSERT INTO topic_terms (topic_id, term, weight)
                    VALUES (:topic_id, :term, :weight)
                    ON CONFLICT (topic_id, term) DO UPDATE SET
                        weight = EXCLUDED.weight
                """)
                
                result = conn.execute(stmt, terms_data)
                conn.commit()
                
                logger.info(f"Upserted {len(terms_data)} topic terms")
                return len(terms_data)
                
        except SQLAlchemyError as e:
            logger.error(f"Error upserting topic terms: {e}")
            return 0
    
    def upsert_topic_assignments(self, df: pd.DataFrame, doc_id_mapping: Dict[int, int]) -> int:
        """
        Upsert topic assignments to database.
        
        Args:
            df: DataFrame with topic assignments (columns: doc_id, topic_id, probability)
            doc_id_mapping: Mapping from DataFrame index to database document ID
            
        Returns:
            Number of assignments inserted/updated
        """
        if df.empty:
            logger.warning("No topic assignments to upsert")
            return 0
        
        # Prepare data for insertion
        assignments_data = []
        for _, row in df.iterrows():
            # Map DataFrame index to database document ID
            db_doc_id = doc_id_mapping.get(row['doc_id'])
            if db_doc_id is not None:
                assignment_data = {
                    'doc_id': db_doc_id,
                    'topic_id': int(row['topic_id']),
                    'probability': float(row['probability'])
                }
                assignments_data.append(assignment_data)
        
        if not assignments_data:
            logger.warning("No valid assignments to upsert")
            return 0
        
        try:
            with self.engine.connect() as conn:
                stmt = text("""
                    INSERT INTO topic_assignments (doc_id, topic_id, probability, assigned_at)
                    VALUES (:doc_id, :topic_id, :probability, NOW())
                    ON CONFLICT (doc_id, topic_id) DO UPDATE SET
                        probability = EXCLUDED.probability,
                        assigned_at = NOW()
                """)
                
                result = conn.execute(stmt, assignments_data)
                conn.commit()
                
                logger.info(f"Upserted {len(assignments_data)} topic assignments")
                return len(assignments_data)
                
        except SQLAlchemyError as e:
            logger.error(f"Error upserting topic assignments: {e}")
            return 0
    
    def upsert_topic_trends(self, df: pd.DataFrame) -> int:
        """
        Upsert topic trends to database.
        
        Args:
            df: DataFrame with topic trends (columns: topic_id, year, month, doc_count)
            
        Returns:
            Number of trends inserted/updated
        """
        if df.empty:
            logger.warning("No topic trends to upsert")
            return 0
        
        # Prepare data for insertion
        trends_data = []
        for _, row in df.iterrows():
            trend_data = {
                'topic_id': int(row['topic_id']),
                'year': int(row['year']),
                'month': int(row['month']),
                'doc_count': int(row['doc_count'])
            }
            trends_data.append(trend_data)
        
        try:
            with self.engine.connect() as conn:
                stmt = text("""
                    INSERT INTO topic_trends (topic_id, year, month, doc_count)
                    VALUES (:topic_id, :year, :month, :doc_count)
                    ON CONFLICT (topic_id, year, month) DO UPDATE SET
                        doc_count = EXCLUDED.doc_count
                """)
                
                result = conn.execute(stmt, trends_data)
                conn.commit()
                
                logger.info(f"Upserted {len(trends_data)} topic trends")
                return len(trends_data)
                
        except SQLAlchemyError as e:
            logger.error(f"Error upserting topic trends: {e}")
            return 0
    
    def get_document_id_mapping(self, core_ids: List[str]) -> Dict[int, int]:
        """
        Get mapping from DataFrame index to database document ID.
        
        Args:
            core_ids: List of CORE IDs
            
        Returns:
            Mapping from DataFrame index to database document ID
        """
        if not core_ids:
            return {}
        
        try:
            with self.engine.connect() as conn:
                # Create placeholders for IN clause
                placeholders = ','.join([':id' + str(i) for i in range(len(core_ids))])
                params = {f'id{i}': core_id for i, core_id in enumerate(core_ids)}
                
                stmt = text(f"""
                    SELECT id, core_id FROM documents 
                    WHERE core_id IN ({placeholders})
                """)
                
                result = conn.execute(stmt, params)
                mapping = {row.core_id: row.id for row in result}
                
                return mapping
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting document ID mapping: {e}")
            return {}
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for all tables."""
        counts = {}
        tables = ['documents', 'topics', 'topic_terms', 'topic_assignments', 'topic_trends']
        
        try:
            with self.engine.connect() as conn:
                for table in tables:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    counts[table] = count
                    
        except SQLAlchemyError as e:
            logger.error(f"Error getting table counts: {e}")
        
        return counts


if __name__ == "__main__":
    # Test the database writer
    writer = DatabaseWriter()
    if writer.test_connection():
        counts = writer.get_table_counts()
        print("Table counts:")
        for table, count in counts.items():
            print(f"  {table}: {count}")
    else:
        print("Database connection failed")
