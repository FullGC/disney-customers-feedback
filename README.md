# Disney Customer Feedback API 🏰

A FastAPI application that answers natural language questions about Disney parks using customer reviews. The system uses hybrid search combining keyword matching and semantic similarity for improved results.

## Features

- 🔍 **Hybrid Search**: Combines keyword matching and semantic similarity using embeddings
- 🏰 **Disney Parks Support**: Supports multiple Disney locations (California, Hong Kong, Paris)
- 🗺️ **Location Filtering**: Filter reviews by visitor location
- 🤖 **LLM Integration**: Uses GPT-4o-mini for natural language responses
- 📊 **Vector Database**: ChromaDB for semantic search capabilities
- 🚀 **FastAPI**: Modern, fast API with automatic documentation

## Quick Start

### 1. Prerequisites

- Python 3.13+
- Docker & Docker Compose
- OpenAI API key

### 2. Setup Environment

```bash
# Clone and navigate to project
cd disney_customers_feedback_ex

# Create virtual environment and install dependencies
poetry install

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 3. Start ChromaDB

```bash
# Start ChromaDB with Docker Compose
docker-compose up -d

# Verify ChromaDB is running
curl http://localhost:8001/api/v1/heartbeat
```

### 4. Prepare Data

Place your `DisneylandReviews.csv` file in:
```
src/disney_customers_feedback_ex/resources/DisneylandReviews.csv
```

### 5. Start the API Server

```bash
# Activate virtual environment
source env_disney_customers_feedback_ex/bin/activate

# Start the server
PYTHONPATH=src python src/disney_customers_feedback_ex/main.py
```

Or use VS Code debugger (F5) with the "FastAPI: Run Server" configuration.

## API Usage

### Base URL
```
http://localhost:8000
```

### Endpoints

#### 1. Health Check
```bash
GET /health
```

#### 2. Root Information
```bash
GET /
```

#### 3. Query Disney Reviews
```bash
POST /query
Content-Type: application/json

{
  "question": "What do visitors from Australia say about Disneyland in Hong Kong?"
}
```

### Example Queries

Try these natural language questions:

```bash
# Location-specific queries
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What do visitors from Australia say about Disneyland in Hong Kong?"}'

# Seasonal queries  
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is spring a good time to visit Disneyland?"}'

# Crowd queries
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is Disneyland California usually crowded in June?"}'

# Staff queries
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Is the staff in Paris friendly?"}'
```

### Response Format

```json
{
  "question": "What do visitors from Australia say about Disneyland in Hong Kong?",
  "answer": "Visitors from Australia generally enjoyed Hong Kong Disneyland for its compact size and shorter wait times compared to other Disney parks. They appreciated the unique attractions and Chinese cultural elements. However, some noted it's smaller than other Disney parks and recommended visiting during weekdays to avoid crowds.",
  "num_reviews_used": 7
}
```

## API Documentation

Visit the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Architecture

### System Components

1. **FastAPI Server** - REST API endpoints
2. **Review Service** - Loads and searches CSV data using pandas
3. **Embedding Service** - Generates text embeddings using sentence-transformers
4. **Vector Store** - ChromaDB for semantic similarity search
5. **LLM Service** - OpenAI GPT-4o-mini integration

### Search Flow

1. **Query Processing** - Extract location/branch filters from natural language
2. **Pandas Filtering** - Fast metadata filtering (branch, location, dates)
3. **Hybrid Search**:
   - **Keyword Search** - Text matching with relevance scoring
   - **Semantic Search** - Vector similarity using embeddings
   - **Score Combination** - Weighted combination of both approaches
4. **Context Building** - Format top reviews with metadata
5. **LLM Generation** - Send context to GPT-4o-mini for answer generation

## Testing

### Run Integration Tests

```bash
# Start the server first, then run tests
source env_disney_customers_feedback_ex/bin/activate
pytest tests/test_integration.py -v
```

### Test Individual Components

```bash
# Test specific functions
pytest tests/ -k "test_query_endpoint" -v
```

## Development

### Project Structure

```
disney_customers_feedback_ex/
├── src/disney_customers_feedback_ex/
│   ├── main.py                 # FastAPI application
│   ├── core/
│   │   └── logging.py          # Logging configuration  
│   ├── services/
│   │   ├── review_service.py   # CSV data loading & search
│   │   ├── embedding_service.py # Text embedding generation
│   │   ├── vector_store.py     # ChromaDB integration
│   │   └── llm_service.py      # OpenAI integration
│   └── resources/
│       └── DisneylandReviews.csv
├── tests/
│   └── test_integration.py     # API integration tests
├── docker-compose.yml          # ChromaDB setup
├── pyproject.toml             # Dependencies
└── README.md                  # This file
```

### Adding New Features

1. **New Endpoints**: Add to `main.py`
2. **Search Logic**: Modify `review_service.py`
3. **LLM Prompts**: Update `llm_service.py`
4. **Tests**: Add to `tests/` directory

## Troubleshooting

### Common Issues

1. **ChromaDB Connection Failed**
   ```bash
   # Check if ChromaDB is running
   docker-compose ps
   
   # Restart if needed
   docker-compose restart
   ```

2. **CSV Encoding Issues**
   - The system automatically tries multiple encodings (utf-8, latin-1, iso-8859-1, cp1252)
   - Check logs for which encoding was used

3. **OpenAI API Errors**
   - Verify your API key in `.env`
   - Check rate limits and billing status

4. **Memory Issues with Large Datasets**
   - Embeddings are generated in batches of 100
   - Consider reducing batch size for very large datasets

### Logs

Check application logs for detailed information:
```bash
# The application logs to stdout with structured formatting
# Look for startup messages, search operations, and error details
```

## Performance Considerations

- **Embedding Generation**: Done once at startup, cached in ChromaDB
- **Search Performance**: Pandas filtering is very fast for metadata, ChromaDB handles vector similarity
- **Memory Usage**: Full dataset loaded in memory for fast filtering
- **Scalability**: Current setup suitable for datasets up to ~100K reviews

## License

This project is for educational/interview purposes.
