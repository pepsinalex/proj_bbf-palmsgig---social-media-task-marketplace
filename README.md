# PalmsGig - Social Media Task Marketplace

A microservices-based platform connecting social media task creators with workers. Built with FastAPI and designed for scalability and reliability.

## Project Overview

PalmsGig enables businesses and individuals to create social media engagement tasks (likes, follows, shares, comments) and connects them with workers who complete these tasks for rewards. The platform ensures secure transactions, task verification, and fair compensation.

## Architecture

This project follows a microservices architecture with the following services:

- **API Gateway**: Entry point for all client requests, handles routing and authentication
- **User Management**: User registration, authentication, profile management, and OAuth integrations
- **Task Management**: Task creation, assignment, tracking, and completion verification
- **Payment Service**: Payment processing, escrow management, and transaction handling
- **Social Media Integration**: OAuth flows and API integrations for major social platforms

### Technology Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL
- **Cache**: Redis
- **Authentication**: JWT tokens, OAuth 2.0
- **API Documentation**: OpenAPI/Swagger
- **Testing**: Pytest
- **Code Quality**: Black, Ruff, Mypy, pre-commit hooks

## Prerequisites

- Python 3.11 or higher
- Poetry for dependency management
- PostgreSQL 13+
- Redis 6+
- Docker and Docker Compose (optional)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd palmsgig
```

### 2. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your configuration
# Set database URL, Redis URL, API keys, etc.
```

### 4. Database Setup

```bash
# Run database migrations
poetry run alembic upgrade head
```

### 5. Install Pre-commit Hooks

```bash
poetry run pre-commit install
```

## Development Workflow

### Running Services

```bash
# Start API Gateway
poetry run uvicorn src.api_gateway.main:app --reload --port 8000

# Start User Management service
poetry run uvicorn src.user_management.main:app --reload --port 8001

# Start Task Management service
poetry run uvicorn src.task_management.main:app --reload --port 8002

# Start Payment Service
poetry run uvicorn src.payment_service.main:app --reload --port 8003
```

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up

# Start specific service
docker-compose up api-gateway
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_user_registration.py
```

### Code Quality

```bash
# Format code with Black
poetry run black src tests

# Lint with Ruff
poetry run ruff check src tests

# Type check with Mypy
poetry run mypy src
```

### Database Migrations

```bash
# Create new migration
poetry run alembic revision --autogenerate -m "Description of changes"

# Apply migrations
poetry run alembic upgrade head

# Rollback migration
poetry run alembic downgrade -1
```

## API Documentation

Once the services are running, API documentation is available at:

- API Gateway: http://localhost:8000/docs
- User Management: http://localhost:8001/docs
- Task Management: http://localhost:8002/docs
- Payment Service: http://localhost:8003/docs

## Project Structure

```
palmsgig/
├── src/
│   ├── api_gateway/       # API Gateway service
│   ├── user_management/   # User Management service
│   ├── task_management/   # Task Management service
│   ├── payment_service/   # Payment Service
│   ├── social_media/      # Social media integrations
│   └── shared/            # Shared utilities and models
├── tests/                 # Test suites
├── alembic/              # Database migrations
├── scripts/              # Utility scripts
├── k8s/                  # Kubernetes manifests
├── docker-compose.yml    # Docker Compose configuration
├── pyproject.toml        # Project dependencies and configuration
└── README.md            # This file
```

## Contribution Guidelines

1. Create a feature branch from `main`
2. Make your changes following the code style guidelines
3. Write tests for new functionality
4. Ensure all tests pass and code quality checks succeed
5. Submit a pull request with a clear description

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings for classes and functions
- Keep functions focused and single-purpose
- Maintain test coverage above 80%

### Commit Messages

- Use clear, descriptive commit messages
- Start with a verb in present tense (Add, Fix, Update, etc.)
- Reference issue numbers when applicable

## Security

- Never commit sensitive data (.env files, API keys, passwords)
- Use environment variables for configuration
- Follow OWASP security best practices
- Report security vulnerabilities privately to the maintainers

## Support

For questions, issues, or feature requests, please create an issue in the project repository.

## License

[License information to be added]
