"""
Streamlit dashboard for BERTopic CORE online MVP (Basic Version).
This version works without bertopic dependency for basic dashboard functionality.
"""
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import yaml

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from pipelines.db_writer import DatabaseWriter


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        return {
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "min_topic_size": 15
        }


def init_database_connection() -> Optional[DatabaseWriter]:
    """Initialize database connection."""
    try:
        db_writer = DatabaseWriter()
        if db_writer.test_connection():
            return db_writer
        else:
            st.error("Database connection failed. Please check your DATABASE_URL environment variable.")
            return None
    except Exception as e:
        st.error(f"Failed to connect to database: {e}")
        return None


def get_topics_data(db_writer: DatabaseWriter) -> pd.DataFrame:
    """Get topics data from database."""
    try:
        with db_writer.engine.connect() as conn:
            query = """
                SELECT topic_id, label, top_terms, size, updated_at
                FROM topics
                ORDER BY size DESC
            """
            df = pd.read_sql(query, conn)
            return df
    except Exception as e:
        st.error(f"Failed to load topics: {e}")
        return pd.DataFrame()


def get_topic_trends(db_writer: DatabaseWriter, topic_id: int) -> pd.DataFrame:
    """Get topic trends data from database."""
    try:
        with db_writer.engine.connect() as conn:
            query = """
                SELECT year, month, doc_count
                FROM topic_trends
                WHERE topic_id = :topic_id
                ORDER BY year, month
            """
            df = pd.read_sql(query, conn, params={'topic_id': topic_id})
            return df
    except Exception as e:
        st.error(f"Failed to load topic trends: {e}")
        return pd.DataFrame()


def search_documents(db_writer: DatabaseWriter, year_from: int, year_to: int, topic_ids: List[int]) -> pd.DataFrame:
    """Search documents with filters."""
    try:
        with db_writer.engine.connect() as conn:
            # Build query based on filters
            base_query = """
                SELECT DISTINCT d.id, d.title, d.abstract, d.authors, d.venue, d.year, d.url, d.pdf_url
                FROM documents d
            """
            
            if topic_ids:
                base_query += """
                    INNER JOIN topic_assignments ta ON d.id = ta.doc_id
                    WHERE ta.topic_id = ANY(:topic_ids)
                """
                params = {'topic_ids': topic_ids}
            else:
                base_query += " WHERE 1=1"
                params = {}
            
            base_query += " AND d.year BETWEEN :year_from AND :year_to"
            params.update({'year_from': year_from, 'year_to': year_to})
            
            base_query += " ORDER BY d.year DESC, d.id DESC LIMIT 100"
            
            df = pd.read_sql(base_query, conn, params=params)
            return df
    except Exception as e:
        st.error(f"Failed to search documents: {e}")
        return pd.DataFrame()


def get_document_details(db_writer: DatabaseWriter, doc_id: int) -> Dict[str, Any]:
    """Get document details and topic assignments."""
    try:
        with db_writer.engine.connect() as conn:
            # Get document details
            doc_query = """
                SELECT id, title, abstract, authors, venue, year, url, pdf_url
                FROM documents
                WHERE id = :doc_id
            """
            doc_result = conn.execute(doc_query, {'doc_id': doc_id})
            doc_row = doc_result.fetchone()
            
            if not doc_row:
                return {}
            
            # Get topic assignments
            topic_query = """
                SELECT ta.topic_id, ta.probability, t.label
                FROM topic_assignments ta
                INNER JOIN topics t ON ta.topic_id = t.topic_id
                WHERE ta.doc_id = :doc_id
                ORDER BY ta.probability DESC
            """
            topic_result = conn.execute(topic_query, {'doc_id': doc_id})
            topic_rows = topic_result.fetchall()
            
            return {
                'document': dict(doc_row),
                'topics': [dict(row) for row in topic_rows]
            }
    except Exception as e:
        st.error(f"Failed to get document details: {e}")
        return {}


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="BERTopic CORE Research Insights",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 BERTopic CORE Research Insights")
    st.markdown("Explore research topics and trends from CORE API papers")
    
    # Show warning about bertopic dependency
    st.warning("""
    **Note:** This is a basic version of the dashboard. 
    The topic prediction feature is not available due to missing bertopic dependency.
    To enable full functionality, install Microsoft Visual C++ Build Tools and run: `pip install bertopic`
    """)
    
    # Initialize connections
    db_writer = init_database_connection()
    
    if not db_writer:
        st.error("""
        **Database not configured**
        
        To use this dashboard, please:
        1. Set up a PostgreSQL database
        2. Run the database schema: `psql -f db_schema.sql`
        3. Set the DATABASE_URL environment variable
        4. Run the pipeline to populate data
        
        Example DATABASE_URL: `postgresql+psycopg2://user:pass@localhost:5432/coredb`
        """)
        return
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Topics", "Trends", "Search", "Document"])
    
    with tab1:
        st.header("📚 Research Topics")
        
        topics_df = get_topics_data(db_writer)
        
        if not topics_df.empty:
            st.dataframe(
                topics_df,
                column_config={
                    "topic_id": "Topic ID",
                    "label": "Topic Label",
                    "top_terms": "Top Terms",
                    "size": "Document Count",
                    "updated_at": "Last Updated"
                },
                hide_index=True
            )
            
            # Topic size distribution
            fig = px.bar(
                topics_df.head(20),
                x='topic_id',
                y='size',
                title="Top 20 Topics by Document Count",
                labels={'topic_id': 'Topic ID', 'size': 'Document Count'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No topics found. Run the pipeline to generate topics.")
    
    with tab2:
        st.header("📈 Topic Trends")
        
        topics_df = get_topics_data(db_writer)
        
        if not topics_df.empty:
            # Topic selector
            selected_topic = st.selectbox(
                "Select a topic to view trends:",
                options=topics_df['topic_id'].tolist(),
                format_func=lambda x: f"Topic {x}: {topics_df[topics_df['topic_id'] == x]['label'].iloc[0]}"
            )
            
            if selected_topic:
                trends_df = get_topic_trends(db_writer, selected_topic)
                
                if not trends_df.empty:
                    # Create date column for better plotting
                    trends_df['date'] = pd.to_datetime(trends_df[['year', 'month']].assign(day=1))
                    
                    fig = px.line(
                        trends_df,
                        x='date',
                        y='doc_count',
                        title=f"Monthly Document Count for Topic {selected_topic}",
                        labels={'date': 'Date', 'doc_count': 'Document Count'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.dataframe(trends_df, hide_index=True)
                else:
                    st.info(f"No trend data available for Topic {selected_topic}")
        else:
            st.info("No topics found. Run the pipeline to generate topics.")
    
    with tab3:
        st.header("🔍 Search Documents")
        
        # Search filters
        col1, col2 = st.columns(2)
        
        with col1:
            year_from = st.number_input("From Year", min_value=2000, max_value=2030, value=2021)
            year_to = st.number_input("To Year", min_value=2000, max_value=2030, value=2025)
        
        with col2:
            topics_df = get_topics_data(db_writer)
            if not topics_df.empty:
                selected_topics = st.multiselect(
                    "Filter by Topics (optional):",
                    options=topics_df['topic_id'].tolist(),
                    format_func=lambda x: f"Topic {x}: {topics_df[topics_df['topic_id'] == x]['label'].iloc[0]}"
                )
            else:
                selected_topics = []
        
        if st.button("Search"):
            results_df = search_documents(db_writer, year_from, year_to, selected_topics)
            
            if not results_df.empty:
                st.success(f"Found {len(results_df)} documents")
                
                # Display results
                for _, row in results_df.iterrows():
                    with st.expander(f"{row['title']} ({row['year']})"):
                        st.write(f"**Authors:** {row['authors']}")
                        st.write(f"**Venue:** {row['venue']}")
                        st.write(f"**Abstract:** {row['abstract'][:300]}...")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if row['url']:
                                st.link_button("View Paper", row['url'])
                        with col2:
                            if row['pdf_url']:
                                st.link_button("Download PDF", row['pdf_url'])
            else:
                st.info("No documents found matching your criteria.")
    
    with tab4:
        st.header("📄 Document Details")
        
        # Document selector
        doc_id = st.number_input("Enter Document ID:", min_value=1, value=1)
        
        if st.button("Load Document"):
            doc_details = get_document_details(db_writer, doc_id)
            
            if doc_details:
                doc = doc_details['document']
                topics = doc_details['topics']
                
                st.subheader(doc['title'])
                st.write(f"**Authors:** {doc['authors']}")
                st.write(f"**Venue:** {doc['venue']}")
                st.write(f"**Year:** {doc['year']}")
                
                st.write("**Abstract:**")
                st.write(doc['abstract'])
                
                # Links
                col1, col2 = st.columns(2)
                with col1:
                    if doc['url']:
                        st.link_button("View Paper", doc['url'])
                with col2:
                    if doc['pdf_url']:
                        st.link_button("Download PDF", doc['pdf_url'])
                
                # Topic assignments
                if topics:
                    st.subheader("Topic Assignments")
                    topic_df = pd.DataFrame(topics)
                    st.dataframe(
                        topic_df,
                        column_config={
                            "topic_id": "Topic ID",
                            "probability": st.column_config.NumberColumn(
                                "Probability",
                                format="%.3f"
                            ),
                            "label": "Topic Label"
                        },
                        hide_index=True
                    )
                    
                    # Probability chart
                    fig = px.bar(
                        topic_df,
                        x='topic_id',
                        y='probability',
                        title="Topic Assignment Probabilities",
                        labels={'topic_id': 'Topic ID', 'probability': 'Probability'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No topic assignments found for this document.")
            else:
                st.error("Document not found.")


if __name__ == "__main__":
    main()
