#!/bin/bash
set -e

# Start the FastAPI application
exec uvicorn src.api_gateway.main:app --host 0.0.0.0 --port ${PORT:-8000}
