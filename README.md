# PalmsGig - Social Media Task Marketplace

A FastAPI-based microservices platform connecting task creators with social media users to complete engagement tasks across multiple platforms.

## Architecture Overview

PalmsGig is built on a microservices architecture with the following core services:

- **API Gateway**: Central entry point for client requests with authentication and routing
- **User Management**: User registration, authentication, OAuth, and profile management
- **Task Management**: Task creation, discovery, assignment, and completion workflow
- **Payment Service**: Wallet management, escrow, and payment processing
- **Social Media Service**: Integration with social platforms for account verification

## Prerequisites

- **Python**: 3.11 or higher
- **Poetry**: For dependency management
- **PostgreSQL**: Database backend
- **Redis**: Caching and session management

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd palmsgig
```

### 2. Install Dependencies

```bash
poetry install
```

### 3. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your configuration values.

### 4. Database Setup

```bash
# Run database migrations
poetry run alembic upgrade head
```

### 5. Start Development Server

```bash
poetry run uvicorn src.api_gateway.main:app --reload
```

## Development Workflow

### Code Quality

The project uses pre-commit hooks for automated code quality checks:

```bash
# Install pre-commit hooks
poetry run pre-commit install

# Run checks manually
poetry run pre-commit run --all-files
```

### Formatting

```bash
# Format code with black
poetry run black src/ tests/

# Lint with ruff
poetry run ruff check src/ tests/
```

### Type Checking

```bash
poetry run mypy src/
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
palmsgig/
├── src/
│   ├── api_gateway/       # API Gateway service
│   ├── user_management/   # User Management service
│   ├── task_management/   # Task Management service
│   ├── payment_service/   # Payment service
│   ├── social_media/      # Social Media integration
│   └── shared/            # Shared utilities and models
├── tests/                 # Test suite
├── alembic/              # Database migrations
└── docs/                 # Project documentation
```

## Contribution Guidelines

1. Create a feature branch from `main`
2. Follow the existing code style and patterns
3. Write tests for new functionality
4. Ensure all tests pass and code quality checks succeed
5. Submit a pull request with a clear description

## License

[License information to be added]
