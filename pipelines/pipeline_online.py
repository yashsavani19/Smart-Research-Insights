"""
Online BERTopic pipeline for topic modeling with incremental updates.
"""
import argparse
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger
try:
    import yaml
except ImportError:
    raise ImportError("PyYAML is required. Please install it with: pip install pyyaml")

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    else:
        logger.warning("config.yaml not found, using defaults")
        return {
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "min_topic_size": 15,
            "min_df": 5,
            "max_df": 0.9,
            "decay": 0.01
        }


class OnlineBERTopicPipeline:
    """Online BERTopic pipeline with incremental updates."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.embedding_model = config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
        self.min_topic_size = config.get("min_topic_size", 15)
        self.min_df = config.get("min_df", 5)
        self.max_df = config.get("max_df", 0.9)
        self.decay = config.get("decay", 0.01)
        
        self.model = None
        self.encoder = None
        self.artifacts_dir = Path("models/artifacts")
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
    
    def _create_texts(self, df: pd.DataFrame) -> List[str]:
        """Create text documents from title and abstract."""
        texts = []
        for _, row in df.iterrows():
            title = str(row.get('title', ''))
            abstract = str(row.get('abstract', ''))
            text = f"{title} {abstract}".strip()
            if text:
                texts.append(text)
            else:
                texts.append("")  # Empty text for documents without content
        return texts
    
    def _create_vectorizer(self) -> CountVectorizer:
        """Create the online count vectorizer."""
        return CountVectorizer(
            stop_words="english",
            min_df=self.min_df,
            max_df=self.max_df,
            decay=self.decay
        )
    
    def _load_encoder(self):
        """Load the sentence transformer encoder."""
        if self.encoder is None:
            logger.info(f"Loading encoder: {self.embedding_model}")
            self.encoder = SentenceTransformer(self.embedding_model)
    
    def _create_model(self) -> BERTopic:
        """Create a new BERTopic model."""
        vectorizer = self._create_vectorizer()
        
        model = BERTopic(
            vectorizer_model=vectorizer,
            min_topic_size=self.min_topic_size,
            verbose=True
        )
        
        return model
    
    def init_model(self, batch_path: str) -> None:
        """
        Initialize the BERTopic model with initial data.
        
        Args:
            batch_path: Path to the Parquet file with documents
        """
        logger.info(f"Initializing BERTopic model with {batch_path}")
        
        # Load data
        df = pd.read_parquet(batch_path)
        logger.info(f"Loaded {len(df)} documents")
        
        # Create texts
        texts = self._create_texts(df)
        logger.info(f"Created {len(texts)} text documents")
        
        # Load encoder
        self._load_encoder()
        
        # Create and fit model
        self.model = self._create_model()
        
        logger.info("Encoding documents...")
        embeddings = self.encoder.encode(texts, show_progress_bar=True)
        
        logger.info("Fitting BERTopic model...")
        topics, probs = self.model.fit_transform(texts, embeddings)
        
        # Save model
        model_path = self.artifacts_dir / "bertopic_light"
        self.model.save(str(model_path), serialization="safetensors")
        logger.info(f"Saved model to {model_path}")
        
        # Log model info
        topic_info = self.model.get_topic_info()
        logger.info(f"Model trained with {len(topic_info)} topics")
        logger.info(f"Topic size range: {topic_info['Count'].min()}-{topic_info['Count'].max()}")
    
    def update_model(self, batch_path: str) -> None:
        """
        Update the BERTopic model with new data.
        
        Args:
            batch_path: Path to the Parquet file with new documents
        """
        logger.info(f"Updating BERTopic model with {batch_path}")
        
        # Load existing model
        model_path = self.artifacts_dir / "bertopic_light"
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}. Run init first.")
        
        self.model = BERTopic.load(str(model_path))
        logger.info("Loaded existing model")
        
        # Load new data
        df = pd.read_parquet(batch_path)
        logger.info(f"Loaded {len(df)} new documents")
        
        # Create texts
        texts = self._create_texts(df)
        logger.info(f"Created {len(texts)} text documents")
        
        # Load encoder
        self._load_encoder()
        
        # Encode new documents
        logger.info("Encoding new documents...")
        embeddings = self.encoder.encode(texts, show_progress_bar=True)
        
        # Transform new documents
        logger.info("Transforming new documents...")
        topics, probs = self.model.transform(texts, embeddings)
        
        # Update topics with new documents
        logger.info("Updating topics...")
        self.model.update_topics(texts)
        
        # Save updated model
        self.model.save(str(model_path), serialization="safetensors")
        logger.info(f"Saved updated model to {model_path}")
        
        # Log model info
        topic_info = self.model.get_topic_info()
        logger.info(f"Updated model has {len(topic_info)} topics")
    
    def get_topic_summary(self) -> pd.DataFrame:
        """Get topic summary dataframe."""
        if self.model is None:
            raise ValueError("Model not loaded. Run init or update first.")
        
        topic_info = self.model.get_topic_info()
        return topic_info
    
    def get_topic_assignments(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get topic assignments for documents.
        
        Args:
            df: DataFrame with documents
            
        Returns:
            DataFrame with doc_id, topic_id, probability
        """
        if self.model is None:
            raise ValueError("Model not loaded. Run init or update first.")
        
        texts = self._create_texts(df)
        
        # Load encoder if needed
        self._load_encoder()
        
        # Transform documents
        embeddings = self.encoder.encode(texts, show_progress_bar=True)
        topics, probs = self.model.transform(texts, embeddings)
        
        # Create assignments dataframe
        assignments = []
        for i, (topic, prob) in enumerate(zip(topics, probs)):
            if topic != -1:  # Skip outlier documents
                assignments.append({
                    'doc_id': i,
                    'topic_id': int(topic),
                    'probability': float(prob[topic]) if prob is not None else 0.0
                })
        
        return pd.DataFrame(assignments)
    
    def get_topic_terms(self) -> pd.DataFrame:
        """Get topic terms with weights."""
        if self.model is None:
            raise ValueError("Model not loaded. Run init or update first.")
        
        topics = self.model.get_topics()
        terms_data = []
        
        for topic_id, terms in topics.items():
            for term, weight in terms:
                terms_data.append({
                    'topic_id': topic_id,
                    'term': term,
                    'weight': weight
                })
        
        return pd.DataFrame(terms_data)
    
    def transform_text(self, text: str) -> Tuple[int, float]:
        """
        Transform a single text and return topic assignment.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (topic_id, probability)
        """
        if self.model is None:
            raise ValueError("Model not loaded. Run init or update first.")
        
        # Load encoder if needed
        self._load_encoder()
        
        # Transform text
        embedding = self.encoder.encode([text])
        topics, probs = self.model.transform([text], embedding)
        
        topic_id = int(topics[0])
        probability = float(probs[0][topics[0]]) if probs[0] is not None and topics[0] != -1 else 0.0
        
        return topic_id, probability


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Online BERTopic pipeline")
    parser.add_argument("--mode", choices=["init", "update"], required=True, help="Pipeline mode")
    parser.add_argument("--batch_path", type=str, required=True, help="Path to Parquet batch file")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    
    # Create pipeline
    pipeline = OnlineBERTopicPipeline(config)
    
    if args.mode == "init":
        pipeline.init_model(args.batch_path)
    elif args.mode == "update":
        pipeline.update_model(args.batch_path)
    
    # Print summary
    try:
        topic_summary = pipeline.get_topic_summary()
        print(f"\nTopic Summary:")
        print(f"Total topics: {len(topic_summary)}")
        print(f"Topic size range: {topic_summary['Count'].min()}-{topic_summary['Count'].max()}")
        
        # Show top 5 topics
        print(f"\nTop 5 topics:")
        top_topics = topic_summary.head(5)
        for _, topic in top_topics.iterrows():
            print(f"  Topic {topic['Topic']}: {topic['Count']} docs - {topic['Name']}")
            
    except Exception as e:
        logger.error(f"Error getting topic summary: {e}")


if __name__ == "__main__":
    main()
