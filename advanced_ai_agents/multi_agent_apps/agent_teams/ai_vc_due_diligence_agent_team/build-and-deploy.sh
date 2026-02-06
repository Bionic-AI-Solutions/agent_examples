#!/bin/bash

# VC Diligence - Build and Deploy Script
# This script builds both frontend and backend Docker images and deploys them to Kubernetes

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCKER_USERNAME="docker4zerocool"
BACKEND_IMAGE="${DOCKER_USERNAME}/vc-diligence-backend:latest"
FRONTEND_IMAGE="${DOCKER_USERNAME}/vc-diligence-frontend:latest"
NAMESPACE="vc-diligence"

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   VC Diligence - Build and Deploy Script                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo -e "${YELLOW}▶ $1${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Function to handle errors
handle_error() {
    echo -e "${RED}✗ Error: $1${NC}"
    exit 1
}

# Check if we're in the correct directory
if [ ! -f "agent.py" ]; then
    handle_error "agent.py not found. Please run this script from the project root directory."
fi

# Build Backend
print_section "Building Backend Docker Image"
docker build --platform linux/amd64 \
    -t "${BACKEND_IMAGE}" \
    -f backend/Dockerfile \
    . || handle_error "Backend build failed"
echo -e "${GREEN}✓ Backend image built successfully${NC}"

# Build Frontend
print_section "Building Frontend Docker Image"
docker build --platform linux/amd64 \
    -t "${FRONTEND_IMAGE}" \
    -f frontend/Dockerfile \
    . || handle_error "Frontend build failed"
echo -e "${GREEN}✓ Frontend image built successfully${NC}"

# Push Backend
print_section "Pushing Backend Image to Docker Hub"
docker push "${BACKEND_IMAGE}" || handle_error "Backend push failed"
echo -e "${GREEN}✓ Backend image pushed successfully${NC}"

# Push Frontend
print_section "Pushing Frontend Image to Docker Hub"
docker push "${FRONTEND_IMAGE}" || handle_error "Frontend push failed"
echo -e "${GREEN}✓ Frontend image pushed successfully${NC}"

# Deploy to Kubernetes
print_section "Deploying to Kubernetes"

# Apply namespace
echo "Ensuring namespace exists..."
kubectl apply -f k8s/namespace.yaml 2>/dev/null || echo "Namespace already exists"

# Apply secrets and configmap (includes email SMTP + Clerk auth config)
echo "Applying secrets and configmap..."
kubectl apply -f k8s/secret.yaml || handle_error "Secret apply failed"
kubectl apply -f k8s/configmap.yaml || handle_error "ConfigMap apply failed"
echo -e "${GREEN}✓ Secrets and configmap applied${NC}"

# Apply PVCs (if they don't exist)
echo "Ensuring persistent volumes are created..."
kubectl apply -f k8s/frontend/pvc.yaml 2>/dev/null || echo "Frontend PVC already exists"
kubectl apply -f k8s/backend/pvc.yaml 2>/dev/null || echo "Backend PVC already exists"
kubectl apply -f k8s/postgres/pvc.yaml 2>/dev/null || echo "Postgres PVC already exists"

# Apply services
echo "Applying services..."
kubectl apply -f k8s/backend/service.yaml || handle_error "Backend service apply failed"
kubectl apply -f k8s/frontend/service.yaml || handle_error "Frontend service apply failed"
kubectl apply -f k8s/postgres/service.yaml 2>/dev/null || echo "Postgres service already exists"

# Apply deployments (picks up new env vars, image references, etc.)
echo "Applying deployments..."
kubectl apply -f k8s/postgres/deployment.yaml || handle_error "Postgres deployment apply failed"
kubectl apply -f k8s/backend/deployment.yaml || handle_error "Backend deployment apply failed"
kubectl apply -f k8s/frontend/deployment.yaml || handle_error "Frontend deployment apply failed"
echo -e "${GREEN}✓ Deployments applied${NC}"

# Apply ingress (if exists)
if [ -d "k8s/ingress" ]; then
    echo "Applying ingress..."
    kubectl apply -f k8s/ingress/ 2>/dev/null || echo "Ingress apply skipped"
fi

# Restart deployments to pick up new images
echo "Restarting backend deployment..."
kubectl rollout restart deployment/backend -n ${NAMESPACE} || handle_error "Backend rollout failed"
echo -e "${GREEN}✓ Backend deployment restarted${NC}"

echo "Restarting frontend deployment..."
kubectl rollout restart deployment/frontend -n ${NAMESPACE} || handle_error "Frontend rollout failed"
echo -e "${GREEN}✓ Frontend deployment restarted${NC}"

# Wait for deployments to be ready
print_section "Waiting for Deployments"

echo "Waiting for backend deployment..."
kubectl rollout status deployment/backend -n ${NAMESPACE} --timeout=120s || handle_error "Backend deployment timeout"
echo -e "${GREEN}✓ Backend deployment ready${NC}"

echo "Waiting for frontend deployment..."
kubectl rollout status deployment/frontend -n ${NAMESPACE} --timeout=120s || handle_error "Frontend deployment timeout"
echo -e "${GREEN}✓ Frontend deployment ready${NC}"

# Show deployment status
print_section "Deployment Status"
kubectl get pods -n ${NAMESPACE}

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Deployment Complete! ✓                                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Access your application at:"
echo -e "${GREEN}  https://vc.baisoln.com${NC} (Web UI)"
echo -e "${GREEN}  https://vc.baisoln.com/api${NC} (API)"
echo ""
