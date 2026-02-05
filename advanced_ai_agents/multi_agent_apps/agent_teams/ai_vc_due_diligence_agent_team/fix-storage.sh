#!/bin/bash

# Fix ADK storage configuration
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Fixing ADK Storage Configuration${NC}"
echo ""

# Rebuild frontend with local storage enabled
echo -e "${YELLOW}▶ Building frontend image with persistent storage...${NC}"
docker build --platform linux/amd64 \
    -t docker4zerocool/vc-diligence-frontend:latest \
    -f frontend/Dockerfile \
    .

echo -e "${YELLOW}▶ Pushing frontend image...${NC}"
docker push docker4zerocool/vc-diligence-frontend:latest

echo -e "${YELLOW}▶ Applying updated deployment...${NC}"
kubectl apply -f k8s/frontend/deployment.yaml

echo -e "${YELLOW}▶ Deleting old pods to force pull new image...${NC}"
kubectl delete pods -n vc-diligence -l app=frontend

echo ""
echo -e "${GREEN}✓ Storage configuration fixed!${NC}"
echo -e "Sessions and artifacts will now persist across pod restarts."
