#!/bin/bash

# Build and deploy VC Diligence Frontend
set -e

echo "🏗️  Building frontend Docker image..."
cd "$(dirname "$0")/.."

# Build the frontend image
docker build --platform linux/amd64 \
  -t docker4zerocool/vc-diligence-frontend:latest \
  -f frontend/Dockerfile \
  .

echo "📤 Pushing to Docker Hub..."
docker push docker4zerocool/vc-diligence-frontend:latest

echo "🚀 Deploying to Kubernetes..."
kubectl apply -f k8s/frontend/

echo "🔄 Updating ingress..."
kubectl apply -f k8s/ingress/kong-ingress.yaml

echo "⏳ Waiting for deployment..."
kubectl rollout status deployment/frontend -n vc-diligence

echo "✅ Frontend deployed successfully!"
echo "🌐 Access at: https://vc.baisoln.com"
