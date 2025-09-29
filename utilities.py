"""
Utility functions for the Research Insights application
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import ssl

# Download NLTK data if needed
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

def clean_text(text: str) -> str:
    """Clean and preprocess text for analysis"""
    if pd.isna(text):
        return ""
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove special characters and digits
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    return text

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """Extract keywords from text"""
    if not text:
        return []
    
    # Tokenize
    tokens = word_tokenize(text.lower())
    
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    keywords = [word for word in tokens if word not in stop_words and len(word) > 3]
    
    # Count frequency
    from collections import Counter
    word_freq = Counter(keywords)
    
    # Return top N keywords
    return [word for word, _ in word_freq.most_common(top_n)]

def calculate_theme_relevance(abstract: str, theme_keywords: Dict[str, List[str]]) -> Dict[str, float]:
    """Calculate relevance scores for each Babcock theme"""
    
    # Define keywords for each theme
    if not theme_keywords:
        theme_keywords = {
            'Advanced Manufacturing': ['manufacturing', 'robotics', 'automation', '3d printing', 'factory', 'production', 'industrial'],
            'Advanced Materials': ['materials', 'composites', 'nanomaterials', 'polymers', 'alloys', 'ceramics', 'coatings'],
            'Advanced Sensors': ['sensor', 'sensing', 'detection', 'monitoring', 'measurement', 'instrumentation', 'transducer'],
            'AI and Automation': ['artificial intelligence', 'machine learning', 'deep learning', 'neural network', 'algorithm', 'automation'],
            'Connectivity and Communications': ['5g', 'wireless', 'network', 'communication', 'telecommunications', 'broadband', 'internet'],
            'Data Integration, Computing and Analysis': ['data', 'analytics', 'computing', 'cloud', 'database', 'integration', 'processing'],
            'Energy and Sustainability': ['energy', 'renewable', 'sustainable', 'solar', 'wind', 'battery', 'green', 'environmental'],
            'Human Performance Augmentation': ['human', 'augmentation', 'wearable', 'ergonomics', 'interface', 'enhancement', 'cognitive'],
            'Information and Communication Security': ['security', 'cybersecurity', 'encryption', 'privacy', 'authentication', 'blockchain', 'cryptography']
        }
    
    abstract_lower = abstract.lower() if abstract else ""
    relevance_scores = {}
    
    for theme, keywords in theme_keywords.items():
        score = sum(1 for keyword in keywords if keyword in abstract_lower)
        relevance_scores[theme] = score / len(keywords) if keywords else 0
    
    return relevance_scores

def generate_research_summary(papers_df: pd.DataFrame) -> Dict:
    """Generate a summary of research insights"""
    
    summary = {
        'total_papers': len(papers_df),
        'universities': papers_df['university'].nunique() if 'university' in papers_df.columns else 0,
        'date_range': {
            'start': papers_df['year'].min() if 'year' in papers_df.columns else None,
            'end': papers_df['year'].max() if 'year' in papers_df.columns else None
        },
        'top_universities': [],
        'top_themes': [],
        'emerging_topics': []
    }
    
    # Top universities by paper count
    if 'university' in papers_df.columns:
        top_unis = papers_df['university'].value_counts().head(5)
        summary['top_universities'] = [(uni, count) for uni, count in top_unis.items()]
    
    # Top themes
    if 'babcock_theme' in papers_df.columns:
        top_themes = papers_df['babcock_theme'].value_counts().head(5)
        summary['top_themes'] = [(theme, count) for theme, count in top_themes.items()]
    
    return summary

def create_collaboration_network(papers_df: pd.DataFrame) -> Dict:
    """Create collaboration network data from papers"""
    
    collaborations = {}
    
    if 'university' not in papers_df.columns:
        return collaborations
    
    # Group papers by similar topics/themes
    if 'babcock_theme' in papers_df.columns:
        for theme in papers_df['babcock_theme'].unique():
            theme_papers = papers_df[papers_df['babcock_theme'] == theme]
            unis = theme_papers['university'].unique()
            
            if len(unis) > 1:
                collaborations[theme] = list(unis)
    
    return collaborations

def calculate_diversity_index(papers_df: pd.DataFrame, column: str = 'topic') -> float:
    """Calculate diversity index (Shannon entropy) for topics or themes"""
    
    if column not in papers_df.columns:
        return 0.0
    
    # Count occurrences
    counts = papers_df[column].value_counts()
    probabilities = counts / len(papers_df)
    
    # Calculate Shannon entropy
    entropy = -sum(p * np.log(p) for p in probabilities if p > 0)
    
    # Normalize to 0-1 scale
    max_entropy = np.log(len(counts))
    diversity_index = entropy / max_entropy if max_entropy > 0 else 0
    
    return diversity_index

def identify_research_gaps(papers_df: pd.DataFrame, all_themes: List[str]) -> List[str]:
    """Identify potential research gaps based on theme coverage"""
    
    gaps = []
    
    if 'babcock_theme' not in papers_df.columns:
        return gaps
    
    theme_counts = papers_df['babcock_theme'].value_counts()
    
    # Find themes with low coverage
    avg_count = theme_counts.mean()
    for theme in all_themes:
        if theme not in theme_counts or theme_counts[theme] < avg_count * 0.5:
            gaps.append(theme)
    
    return gaps

def format_paper_citation(paper: pd.Series) -> str:
    """Format a paper as a citation string"""
    
    authors = paper.get('authors', 'Unknown Authors')
    title = paper.get('title', 'Untitled')
    year = paper.get('year', 'n.d.')
    university = paper.get('university', '')
    
    citation = f"{authors} ({year}). {title}. {university}"
    
    if paper.get('doi'):
        citation += f" DOI: {paper['doi']}"
    
    return citation

def detect_trending_keywords(papers_df: pd.DataFrame, window_size: int = 6) -> List[Tuple[str, float]]:
    """Detect trending keywords over time"""
    
    trending = []
    
    if 'abstract' not in papers_df.columns or 'year' not in papers_df.columns:
        return trending
    
    # Extract keywords from recent papers
    recent_papers = papers_df[papers_df['year'] >= papers_df['year'].max()]
    older_papers = papers_df[papers_df['year'] < papers_df['year'].max()]
    
    if len(recent_papers) > 0 and len(older_papers) > 0:
        recent_keywords = []
        older_keywords = []
        
        for abstract in recent_papers['abstract'].dropna():
            recent_keywords.extend(extract_keywords(abstract, top_n=5))
        
        for abstract in older_papers['abstract'].dropna():
            older_keywords.extend(extract_keywords(abstract, top_n=5))
        
        # Calculate frequency change
        from collections import Counter
        recent_freq = Counter(recent_keywords)
        older_freq = Counter(older_keywords)
        
        for keyword in recent_freq:
            recent_count = recent_freq[keyword]
            older_count = older_freq.get(keyword, 0)
            
            if older_count > 0:
                growth_rate = (recent_count - older_count) / older_count
                if growth_rate > 0.5:  # 50% growth threshold
                    trending.append((keyword, growth_rate))
        
        # Sort by growth rate
        trending.sort(key=lambda x: x[1], reverse=True)
    
    return trending[:10]  # Return top 10 trending keywords

def validate_core_api_response(response: Dict) -> bool:
    """Validate CORE API response structure"""
    
    if not isinstance(response, dict):
        return False
    
    if 'results' not in response:
        return False
    
    if not isinstance(response['results'], list):
        return False
    
    return True

def estimate_processing_time(n_papers: int, n_universities: int) -> str:
    """Estimate processing time for fetching and analyzing papers"""
    
    # Rough estimates
    fetch_time = n_universities * 2  # 2 seconds per university
    analysis_time = n_papers * 0.1  # 0.1 seconds per paper for topic modeling
    
    total_seconds = fetch_time + analysis_time
    
    if total_seconds < 60:
        return f"{int(total_seconds)} seconds"
    else:
        return f"{int(total_seconds / 60)} minutes"