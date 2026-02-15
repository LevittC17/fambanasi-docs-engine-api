# Fambanasi Docs Engine API

FastAPI backend for the Git-Sync Documentation Engine - handles CMS operations, GitHub integration, and document management.

## Overview

This is the backend API that powers the documentation engine, providing:

- **GitHub Integration**: Seamless bidirectional sync between CMS and Git repository
- **Document Management**: CRUD operations for documentation with version control
- **Authentication**: Supabase-based auth with JWT tokens and RBAC
- **Media Handling**: Image upload and optimization with Supabase Storage
- **Search Support**: Metadata management for Pagefind integration
- **Audit Logging**: Complete tracking of all documentation changes

## Tech Stack

- **Python 3.14+**: Latest Python version
- **FastAPI 0.129+**: Modern, high-performance web framework
- **PostgreSQL 18+**: Primary database (via Supabase)
- **SQLAlchemy 2.0**: Async ORM for database operations
- **Supabase**: Authentication, database, and storage
- **GitHub API**: Repository integration via PyGithub
- **Redis**: Caching and rate limiting

## Getting Started

### Prerequisites

- Python 3.14+
- Poetry (dependency management)
- PostgreSQL 18+ (or Supabase account)
- Redis (for caching)
- GitHub Personal Access Token

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/your-org/fambanasi-docs-engine-api.git
   cd fambanasi-docs-engine-api
```

2. **Install dependencies with Poetry**
```bash
   poetry install
```

3. **Set up environment variables**
```bash
   cp .env.example .env
   # Edit .env with your configuration
```

4. **Run database migrations**
```bash
   poetry run alembic upgrade head
```

5. **Start the development server**
```bash
   poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the API documentation**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Project Structure
```
app/
├── api/              # API routes and endpoints
├── core/             # Core configuration and settings
├── db/               # Database models and session management
├── schemas/          # Pydantic schemas for validation
├── services/         # Business logic and external integrations
├── utils/            # Utility functions and helpers
└── middleware/       # Custom middleware components
```

## Development

### Code Quality

We use Ruff for linting and Black for formatting:
```bash
# Lint code
poetry run ruff check app/

# Format code
poetry run black app/

# Type checking
poetry run mypy app/
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=app --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_github_service.py
```

### Database Migrations
```bash
# Create new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

## Deployment

### Docker
```bash
# Build image
docker build -t fambanasi-docs-api .

# Run container
docker run -p 8000:8000 --env-file .env fambanasi-docs-api
```

### Production Deployment

Recommended platforms:
- **Railway**: Easy deployment with automatic HTTPS
- **Render**: Free tier available, good for MVP
- **AWS ECS/Fargate**: Enterprise-grade scaling
- **Google Cloud Run**: Serverless container deployment

## API Documentation

Full API documentation is available at `/docs` when running the server. Key endpoints:

- `POST /api/v1/documents`: Create new document
- `GET /api/v1/documents/{path}`: Retrieve document
- `PUT /api/v1/documents/{path}`: Update document
- `DELETE /api/v1/documents/{path}`: Delete document
- `POST /api/v1/auth/login`: User authentication
- `POST /api/v1/media/upload`: Upload media files

## Contributing

1. Follow PEP 8 style guidelines
2. Write tests for new features
3. Update documentation as needed
4. Create meaningful commit messages

## License

[Your License Here]

## Support

For issues and questions, please contact: team@example.com
