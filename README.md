# BERTopic CORE Online MVP

A minimal, working MVP that ingests English research papers from CORE API, runs an online BERTopic pipeline, stores outputs in PostgreSQL, and serves a Streamlit dashboard for topic exploration and analysis.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker (for database) or PostgreSQL
- CORE API key ([Get one here](https://core.ac.uk/services/api/))

### 1. Setup Environment

```bash
# Clone and setup
git clone <repository-url>
cd Smart-Research-Insights-1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your CORE_API_KEY
```

### 2. Start Database

```bash
# Using Docker (recommended)
make setup-db

# Or manually
make setup-db-manual
```

### 3. Run Smoke Test

```bash
# Quick test with 100 papers
make test-smoke
```

### 4. Launch Dashboard

```bash
make streamlit
```

Visit `http://localhost:8501` to explore the dashboard.

## 📋 Features

### Core Functionality
- **CORE API Integration**: Fetches English research papers (2021-2025)
- **Online BERTopic Pipeline**: Supports incremental model updates
- **PostgreSQL Storage**: Persistent storage with proper indexing
- **Streamlit Dashboard**: Interactive exploration interface

### Dashboard Tabs
- **Topics**: Browse discovered research topics
- **Trends**: View monthly topic trends over time
- **Search**: Filter documents by year and topic
- **Document**: View individual paper details and topic assignments
- **Predict**: On-the-fly topic prediction for new text

## 🛠️ Usage

### Environment Variables

Create a `.env` file with:

```bash
CORE_API_KEY=your_core_api_key_here
DATABASE_URL=postgresql+psycopg2://coreuser:corepass@localhost:5432/coredb
CORE_BASE_URL=https://api.core.ac.uk/v3/search/works
```

### Available Commands

```bash
# Show all available commands
make help

# Database operations
make setup-db              # Start PostgreSQL with Docker
make setup-db-manual       # Manual database setup instructions

# Data ingestion
make ingest               # Ingest 200 papers (2021-2025)
make ingest-full          # Ingest all papers (2021-2025)

# Model operations
make init-model           # Initialize BERTopic model
make update-model         # Update existing model

# Pipeline operations
make run-pipeline         # Complete pipeline (200 papers)
make run-pipeline-full    # Complete pipeline (all papers)
make run-pipeline-no-db   # Pipeline without database

# Dashboard
make streamlit            # Start Streamlit dashboard

# Testing
make test-smoke           # Smoke test with 100 papers

# Maintenance
make clean                # Clean generated files
make clean-all            # Clean everything including Docker
```

### Manual CLI Usage

```bash
# Ingest papers
python ingest/core_ingest.py --from_year 2021 --to_year 2025 --lang en --limit 200

# Initialize model
python pipelines/pipeline_online.py --mode init --batch_path data/clean/2021_2025_en.parquet

# Update model
python pipelines/pipeline_online.py --mode update --batch_path data/clean/2021_2025_en.parquet

# Run end-to-end pipeline
python pipelines/run_end_to_end.py --from_year 2021 --to_year 2025 --lang en --limit 200 --init_if_missing

# Start dashboard
streamlit run app/streamlit_app.py
```

## 📊 Data Flow

1. **Ingestion**: CORE API → Raw JSONL → Cleaned Parquet
2. **Modeling**: Parquet → BERTopic → Topic Assignments
3. **Storage**: All data → PostgreSQL with proper indexing
4. **Dashboard**: PostgreSQL → Streamlit → Interactive UI

## 🗄️ Database Schema

- **documents**: Research papers with metadata
- **topics**: Discovered topic information
- **topic_terms**: Individual terms and weights per topic
- **topic_assignments**: Document-topic assignments with probabilities
- **topic_trends**: Monthly topic trends over time

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
# CORE API Configuration
from_year: 2021
to_year: 2025
language: en

# Model Configuration
embedding_model: sentence-transformers/all-MiniLM-L6-v2
min_topic_size: 15

# Vectorizer Configuration
min_df: 5
max_df: 0.9
decay: 0.01

# Paging Configuration
page_size: 100
max_pages: 200
```

## 🔧 Troubleshooting

### Common Issues

**Database Connection Failed**
```bash
# Check if database is running
docker-compose ps

# Restart database
docker-compose restart db

# Check connection string in .env
```

**CORE API Errors**
```bash
# Verify API key
echo $CORE_API_KEY

# Test API connection
python ingest/core_api.py
```

**Model Loading Issues**
```bash
# Check if model exists
ls -la models/artifacts/

# Reinitialize model
make init-model
```

**Memory Issues**
```bash
# Reduce batch size in config.yaml
page_size: 50
max_pages: 100

# Use smaller limit
python ingest/core_ingest.py --limit 100
```

### Logs

The application uses structured logging with `loguru`. Check logs for detailed error information.

## 📁 Project Structure

```
Smart-Research-Insights-1/
├── app/
│   └── streamlit_app.py          # Streamlit dashboard
├── ingest/
│   ├── core_api.py              # CORE API client
│   └── core_ingest.py           # Data ingestion
├── pipelines/
│   ├── pipeline_online.py       # BERTopic pipeline
│   ├── db_writer.py             # Database operations
│   └── run_end_to_end.py        # End-to-end runner
├── data/
│   ├── raw/                     # Raw JSONL files
│   └── clean/                   # Cleaned Parquet files
├── models/
│   └── artifacts/               # Saved BERTopic models
├── config.yaml                  # Configuration
├── db_schema.sql               # Database schema
├── docker-compose.yml          # Database setup
├── Makefile                    # Common commands
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## 🧪 Testing

### Smoke Test
```bash
make test-smoke
```

This runs a complete pipeline with 100 papers to verify everything works.

### Acceptance Criteria

✅ Running `python ingest/core_ingest.py --from_year 2021 --to_year 2025 --lang en --limit 200` creates both raw JSONL and cleaned Parquet

✅ Running `python pipelines/pipeline_online.py --mode init --batch_path data/clean/2021_2025_en.parquet` trains and saves model

✅ Running `python pipelines/run_end_to_end.py --from_year 2021 --to_year 2025 --lang en --limit 200 --init_if_missing` populates PostgreSQL

✅ Running `streamlit run app/streamlit_app.py` shows working dashboard with all tabs

## 🔒 Security Notes

- Never commit your `.env` file with real secrets
- The `.env.example` file is provided as a template
- Database credentials in Docker Compose are for development only
- Use proper secrets management in production

## 📈 Production Considerations

- Use proper PostgreSQL credentials and connection pooling
- Implement proper error handling and monitoring
- Consider using a task queue for large-scale ingestion
- Add authentication to the Streamlit dashboard
- Implement proper backup strategies for the database

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [CORE API](https://core.ac.uk/) for providing research paper data
- [BERTopic](https://github.com/MaartenGr/BERTopic) for topic modeling
- [Streamlit](https://streamlit.io/) for the dashboard framework
- [PostgreSQL](https://www.postgresql.org/) for data storage
