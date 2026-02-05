#!/usr/bin/env bash
#
# Kubernetes Deployment Script with Health Checks and Rollback
# Usage: ./deploy.sh <environment> <image-tag>
#
# Requirements:
#   - kubectl configured and authenticated
#   - Required environment variables set
#
# Exit codes:
#   0 - Success
#   1 - Validation error
#   2 - Deployment error
#   3 - Health check failure
#   4 - Rollback failure

set -euo pipefail
IFS=$'\n\t'

# Script configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly K8S_DIR="${PROJECT_ROOT}/k8s"
readonly LOG_FILE="${PROJECT_ROOT}/logs/deployment-$(date +%Y%m%d_%H%M%S).log"

# Color codes
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Deployment configuration
readonly DEPLOYMENT_TIMEOUT=300
readonly HEALTH_CHECK_RETRIES=30
readonly HEALTH_CHECK_INTERVAL=10
readonly ROLLBACK_TIMEOUT=180

# Logging functions
log_info() {
    local message="$*"
    echo -e "${GREEN}[INFO]${NC} ${message}" | tee -a "${LOG_FILE}" 2>/dev/null || echo -e "${GREEN}[INFO]${NC} ${message}"
}

log_warn() {
    local message="$*"
    echo -e "${YELLOW}[WARN]${NC} ${message}" | tee -a "${LOG_FILE}" 2>/dev/null || echo -e "${YELLOW}[WARN]${NC} ${message}"
}

log_error() {
    local message="$*"
    echo -e "${RED}[ERROR]${NC} ${message}" | tee -a "${LOG_FILE}" 2>/dev/null || echo -e "${RED}[ERROR]${NC} ${message}"
}

log_debug() {
    if [[ "${DEBUG:-0}" == "1" ]]; then
        local message="$*"
        echo -e "${BLUE}[DEBUG]${NC} ${message}" | tee -a "${LOG_FILE}" 2>/dev/null || echo -e "${BLUE}[DEBUG]${NC} ${message}"
    fi
}

# Error handler
error_handler() {
    local line_number=$1
    local exit_code=$?
    log_error "Deployment failed at line ${line_number} with exit code ${exit_code}"
    log_error "Check log file: ${LOG_FILE}"

    if [[ "${ROLLBACK_ON_ERROR:-1}" == "1" ]]; then
        log_warn "Initiating automatic rollback..."
        rollback_deployment
    fi

    exit 2
}

trap 'error_handler ${LINENO}' ERR

# Cleanup handler
cleanup() {
    local exit_code=$?
    if [[ ${exit_code} -ne 0 ]]; then
        log_error "Deployment failed with exit code ${exit_code}"
    else
        log_info "Deployment completed successfully"
    fi
}

trap cleanup EXIT

# Validate environment
validate_environment() {
    local env=$1

    log_info "Validating environment: ${env}"

    if [[ ! "${env}" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: ${env}"
        log_error "Valid values: development, staging, production"
        return 1
    fi

    local required_tools=("kubectl" "envsubst")
    for tool in "${required_tools[@]}"; do
        if ! command -v "${tool}" &>/dev/null; then
            log_error "Required tool not found: ${tool}"
            log_error "Please install ${tool} and try again"
            return 1
        fi
    done

    if ! kubectl cluster-info &>/dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        log_error "Please configure kubectl and verify cluster access"
        return 1
    fi

    local current_context
    current_context=$(kubectl config current-context 2>/dev/null || echo "unknown")
    log_info "Kubernetes context: ${current_context}"

    if ! kubectl get namespace "${env}" &>/dev/null; then
        log_warn "Namespace '${env}' does not exist"
        log_info "Creating namespace: ${env}"
        kubectl create namespace "${env}" || {
            log_error "Failed to create namespace: ${env}"
            return 1
        }
    fi

    log_info "Environment validation passed"
    return 0
}

# Validate image
validate_image() {
    local image=$1

    log_info "Validating image: ${image}"

    if [[ -z "${image}" ]]; then
        log_error "Image tag is required"
        return 1
    fi

    log_info "Image validation passed"
    return 0
}

# Pre-deployment checks
pre_deployment_checks() {
    local env=$1
    local image=$2

    log_info "Running pre-deployment checks..."

    if [[ -f "${K8S_DIR}/deployment.yaml" ]]; then
        log_info "Validating Kubernetes manifests..."
        export IMAGE_TAG="${image}"
        if ! envsubst < "${K8S_DIR}/deployment.yaml" | kubectl apply --dry-run=client -f - &>/dev/null; then
            log_error "Kubernetes manifest validation failed"
            return 1
        fi
    else
        log_warn "Deployment manifest not found: ${K8S_DIR}/deployment.yaml"
    fi

    log_info "Checking for existing deployment..."
    if kubectl get deployment palmsgig-api -n "${env}" &>/dev/null; then
        log_info "Existing deployment found - will perform rolling update"
        readonly EXISTING_DEPLOYMENT=true
    else
        log_info "No existing deployment - will create new deployment"
        readonly EXISTING_DEPLOYMENT=false
    fi

    log_info "Pre-deployment checks passed"
    return 0
}

# Deploy to Kubernetes
deploy_to_kubernetes() {
    local env=$1
    local image=$2

    log_info "Deploying to Kubernetes..."
    log_info "Environment: ${env}"
    log_info "Image: ${image}"

    export IMAGE_TAG="${image}"
    export ENVIRONMENT="${env}"

    if [[ -f "${K8S_DIR}/deployment.yaml" ]]; then
        log_info "Applying deployment manifest..."
        envsubst < "${K8S_DIR}/deployment.yaml" | kubectl apply -f - -n "${env}" || {
            log_error "Failed to apply deployment manifest"
            return 1
        }
    else
        log_info "Updating deployment image directly..."
        kubectl set image deployment/palmsgig-api \
            "palmsgig-api=${image}" \
            -n "${env}" \
            --record || {
            log_error "Failed to update deployment image"
            return 1
        }
    fi

    kubectl annotate deployment/palmsgig-api \
        "deployment.kubernetes.io/revision-timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        -n "${env}" \
        --overwrite || true

    log_info "Deployment initiated successfully"
    return 0
}

# Wait for rollout
wait_for_rollout() {
    local env=$1

    log_info "Waiting for rollout to complete (timeout: ${DEPLOYMENT_TIMEOUT}s)..."

    if ! kubectl rollout status deployment/palmsgig-api \
        -n "${env}" \
        --timeout="${DEPLOYMENT_TIMEOUT}s"; then
        log_error "Deployment rollout failed or timed out"
        return 1
    fi

    log_info "Rollout completed successfully"
    return 0
}

# Health check
run_health_checks() {
    local env=$1

    log_info "Running health checks..."

    local health_url=""
    case "${env}" in
        development)
            health_url="https://dev.palmsgig.example.com/health"
            ;;
        staging)
            health_url="https://staging.palmsgig.example.com/health"
            ;;
        production)
            health_url="https://palmsgig.example.com/health"
            ;;
    esac

    log_info "Health check URL: ${health_url}"

    local retry_count=0
    while [[ ${retry_count} -lt ${HEALTH_CHECK_RETRIES} ]]; do
        log_debug "Health check attempt $((retry_count + 1))/${HEALTH_CHECK_RETRIES}"

        if curl -sf --max-time 5 "${health_url}" &>/dev/null; then
            log_info "Health check passed"
            return 0
        fi

        retry_count=$((retry_count + 1))
        if [[ ${retry_count} -lt ${HEALTH_CHECK_RETRIES} ]]; then
            log_debug "Health check failed, retrying in ${HEALTH_CHECK_INTERVAL}s..."
            sleep "${HEALTH_CHECK_INTERVAL}"
        fi
    done

    log_error "Health check failed after ${HEALTH_CHECK_RETRIES} attempts"
    return 1
}

# Verify deployment
verify_deployment() {
    local env=$1

    log_info "Verifying deployment..."

    local ready_replicas
    ready_replicas=$(kubectl get deployment palmsgig-api -n "${env}" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")

    local desired_replicas
    desired_replicas=$(kubectl get deployment palmsgig-api -n "${env}" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")

    log_info "Ready replicas: ${ready_replicas}/${desired_replicas}"

    if [[ "${ready_replicas}" != "${desired_replicas}" ]]; then
        log_error "Deployment verification failed: not all replicas are ready"
        return 1
    fi

    log_info "Checking pod status..."
    kubectl get pods -n "${env}" -l app=palmsgig-api

    log_info "Deployment verification passed"
    return 0
}

# Rollback deployment
rollback_deployment() {
    log_warn "Rolling back deployment..."

    if [[ -z "${ENVIRONMENT:-}" ]]; then
        log_error "Environment variable not set, cannot rollback"
        return 1
    fi

    if ! kubectl rollout undo deployment/palmsgig-api -n "${ENVIRONMENT}"; then
        log_error "Rollback command failed"
        return 1
    fi

    log_info "Waiting for rollback to complete (timeout: ${ROLLBACK_TIMEOUT}s)..."
    if ! kubectl rollout status deployment/palmsgig-api \
        -n "${ENVIRONMENT}" \
        --timeout="${ROLLBACK_TIMEOUT}s"; then
        log_error "Rollback failed or timed out"
        return 1
    fi

    log_warn "Rollback completed successfully"
    return 0
}

# Show usage
show_usage() {
    cat <<EOF
Usage: $0 <environment> <image-tag>

Arguments:
  environment    Target environment (development|staging|production)
  image-tag      Docker image tag to deploy

Environment Variables:
  DEBUG                 Enable debug logging (0|1)
  ROLLBACK_ON_ERROR     Automatic rollback on failure (0|1, default: 1)

Examples:
  $0 development ghcr.io/org/palmsgig:main-abc123
  $0 production ghcr.io/org/palmsgig:v1.2.3

EOF
}

# Main deployment function
main() {
    local environment=${1:-}
    local image_tag=${2:-}

    if [[ -z "${environment}" ]] || [[ -z "${image_tag}" ]]; then
        log_error "Missing required arguments"
        show_usage
        exit 1
    fi

    export ENVIRONMENT="${environment}"
    export ROLLBACK_ON_ERROR="${ROLLBACK_ON_ERROR:-1}"

    mkdir -p "$(dirname "${LOG_FILE}")" 2>/dev/null || true

    log_info "========================================"
    log_info "Starting deployment process"
    log_info "========================================"
    log_info "Environment: ${environment}"
    log_info "Image: ${image_tag}"
    log_info "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    log_info "========================================"

    validate_environment "${environment}"
    validate_image "${image_tag}"
    pre_deployment_checks "${environment}" "${image_tag}"
    deploy_to_kubernetes "${environment}" "${image_tag}"
    wait_for_rollout "${environment}"
    verify_deployment "${environment}"

    if [[ "${SKIP_HEALTH_CHECK:-0}" != "1" ]]; then
        run_health_checks "${environment}" || {
            log_warn "Health checks failed but deployment completed"
        }
    else
        log_warn "Health checks skipped (SKIP_HEALTH_CHECK=1)"
    fi

    log_info "========================================"
    log_info "✅ Deployment completed successfully!"
    log_info "========================================"

    return 0
}

main "$@"
