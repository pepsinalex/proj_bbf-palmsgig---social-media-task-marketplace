#!/usr/bin/env bash

# ============================================================================
# PalmsGig Docker Entrypoint Script
# ============================================================================
# This script handles application startup, database connectivity checks,
# migrations, and proper signal handling for graceful shutdown.

set -euo pipefail

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m'

# Script configuration
readonly MAX_DB_RETRIES=30
readonly DB_RETRY_INTERVAL=2
readonly STARTUP_TIMEOUT=60

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

# Signal handlers for graceful shutdown
cleanup() {
    local exit_code=$?
    log_info "Received shutdown signal, cleaning up..."

    # Kill child processes gracefully
    if [[ -n "${APP_PID:-}" ]]; then
        log_info "Stopping application process (PID: ${APP_PID})..."
        kill -TERM "${APP_PID}" 2>/dev/null || true
        wait "${APP_PID}" 2>/dev/null || true
    fi

    log_info "Cleanup completed with exit code ${exit_code}"
    exit "${exit_code}"
}

trap cleanup EXIT INT TERM

# Wait for database to be ready
wait_for_database() {
    log_info "Waiting for database connection..."

    local attempt=1

    while [[ ${attempt} -le ${MAX_DB_RETRIES} ]]; do
        if python -c "
import sys
import asyncpg
import asyncio

async def check_db():
    try:
        conn = await asyncpg.connect('${DATABASE_URL}')
        await conn.close()
        return True
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        return False

if __name__ == '__main__':
    result = asyncio.run(check_db())
    sys.exit(0 if result else 1)
" 2>/dev/null; then
            log_info "Database connection established successfully"
            return 0
        fi

        if [[ ${attempt} -eq ${MAX_DB_RETRIES} ]]; then
            log_error "Failed to connect to database after ${MAX_DB_RETRIES} attempts"
            return 1
        fi

        log_warn "Database not ready yet (attempt ${attempt}/${MAX_DB_RETRIES}), retrying in ${DB_RETRY_INTERVAL}s..."
        sleep "${DB_RETRY_INTERVAL}"
        ((attempt++))
    done

    return 1
}

# Wait for Redis to be ready
wait_for_redis() {
    log_info "Waiting for Redis connection..."

    local redis_host="${REDIS_URL#redis://}"
    redis_host="${redis_host%%/*}"
    local redis_port="${redis_host#*:}"
    redis_host="${redis_host%%:*}"
    redis_port="${redis_port:-6379}"

    local attempt=1

    while [[ ${attempt} -le ${MAX_DB_RETRIES} ]]; do
        if command -v redis-cli &>/dev/null && redis-cli -h "${redis_host}" -p "${redis_port}" ping &>/dev/null; then
            log_info "Redis connection established successfully"
            return 0
        fi

        if python -c "
import sys
import redis

try:
    r = redis.from_url('${REDIS_URL}')
    r.ping()
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
            log_info "Redis connection established successfully"
            return 0
        fi

        if [[ ${attempt} -eq ${MAX_DB_RETRIES} ]]; then
            log_error "Failed to connect to Redis after ${MAX_DB_RETRIES} attempts"
            return 1
        fi

        log_warn "Redis not ready yet (attempt ${attempt}/${MAX_DB_RETRIES}), retrying in ${DB_RETRY_INTERVAL}s..."
        sleep "${DB_RETRY_INTERVAL}"
        ((attempt++))
    done

    return 1
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    if ! command -v alembic &>/dev/null; then
        log_error "Alembic not found, skipping migrations"
        return 0
    fi

    if [[ ! -f "alembic.ini" ]]; then
        log_warn "alembic.ini not found, skipping migrations"
        return 0
    fi

    if alembic upgrade head; then
        log_info "Database migrations completed successfully"
        return 0
    else
        log_error "Database migrations failed"
        return 1
    fi
}

# Health check function
health_check() {
    local max_attempts=10
    local attempt=1

    log_info "Performing health check..."

    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -f -s http://localhost:8000/health &>/dev/null; then
            log_info "Health check passed"
            return 0
        fi

        log_warn "Health check failed (attempt ${attempt}/${max_attempts}), retrying..."
        sleep 2
        ((attempt++))
    done

    log_error "Health check failed after ${max_attempts} attempts"
    return 1
}

# Validate environment variables
validate_environment() {
    log_info "Validating environment configuration..."

    local required_vars=(
        "DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
        "JWT_SECRET"
    )

    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("${var}")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi

    # Warn about insecure defaults
    if [[ "${SECRET_KEY:-}" == *"dev-secret"* ]] || [[ "${JWT_SECRET:-}" == *"dev-jwt"* ]]; then
        if [[ "${ENVIRONMENT:-development}" != "development" ]]; then
            log_error "Insecure default secrets detected in non-development environment"
            return 1
        fi
        log_warn "Using default development secrets - DO NOT use in production!"
    fi

    log_info "Environment validation passed"
    return 0
}

# Main execution
main() {
    log_info "Starting PalmsGig application initialization..."
    log_info "Environment: ${ENVIRONMENT:-development}"
    log_info "Debug mode: ${DEBUG:-False}"

    # Validate environment
    if ! validate_environment; then
        log_error "Environment validation failed"
        exit 1
    fi

    # Wait for services
    if ! wait_for_database; then
        log_error "Database is not available"
        exit 1
    fi

    if ! wait_for_redis; then
        log_error "Redis is not available"
        exit 1
    fi

    # Run migrations if in production or explicitly enabled
    if [[ "${RUN_MIGRATIONS:-auto}" == "true" ]] || \
       [[ "${RUN_MIGRATIONS:-auto}" == "auto" && "${ENVIRONMENT:-development}" != "development" ]]; then
        if ! run_migrations; then
            log_error "Migration failed, aborting startup"
            exit 1
        fi
    else
        log_info "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS:-auto})"
    fi

    log_info "Starting application with command: $*"

    # Start application in background to allow signal handling
    "$@" &
    APP_PID=$!

    log_info "Application started with PID ${APP_PID}"

    # Wait for the application to be ready
    sleep 5

    # Wait for application process
    wait "${APP_PID}"
    local exit_code=$?

    log_info "Application exited with code ${exit_code}"
    exit "${exit_code}"
}

# Execute main function with all arguments
main "$@"
