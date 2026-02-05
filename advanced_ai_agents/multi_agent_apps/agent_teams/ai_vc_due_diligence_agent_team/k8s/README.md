# VC Due Diligence Web App - Kubernetes Deployment Guide

This guide will help you deploy the AI VC Due Diligence agent team as a web application on your local Kubernetes cluster with Kong ingress.

## Prerequisites

- Kubernetes cluster (minikube, kind, k3s, or Rancher Desktop)
- kubectl CLI installed and configured
- Kong Ingress Controller installed
- cert-manager installed (for SSL/TLS)
- Docker Hub account
- DNS configured: vc.baisoln.com → Kong ingress external IP

## Deployment Overview

The application consists of:
- **Backend**: FastAPI server wrapping ADK agents (port 8000)
- **PostgreSQL**: Database for task tracking (port 5432)
- **Kong Ingress**: Routes traffic from vc.baisoln.com to backend
- **cert-manager**: Automated SSL certificates via Let's Encrypt

## Step 1: Build and Push Docker Images

```bash
# Navigate to project directory
cd /workspace/awesome-llm-apps/advanced_ai_agents/multi_agent_apps/agent_teams/ai_vc_due_diligence_agent_team

# Login to Docker Hub
docker login

# Build backend image
# IMPORTANT: Replace 'your-dockerhub-username' with your actual Docker Hub username
docker build -t your-dockerhub-username/vc-diligence-backend:latest -f backend/Dockerfile .

# Push to Docker Hub
docker push your-dockerhub-username/vc-diligence-backend:latest
```

**Note**: After pushing, update `k8s/backend/deployment.yaml` to use your Docker Hub username.

## Step 2: Configure Secrets

Edit `k8s/secret.yaml` to set your actual credentials:

```yaml
stringData:
  # Replace with your actual Google API key
  GOOGLE_API_KEY: "your_actual_google_api_key"

  # Change database password in production
  POSTGRES_PASSWORD: "your_secure_password"

  # Update DATABASE_URL with your new password
  DATABASE_URL: "postgresql+asyncpg://vcuser:your_secure_password@postgres-service:5432/vc_diligence"
```

## Step 3: Update Image References

Edit `k8s/backend/deployment.yaml` and replace `your-dockerhub-username` with your actual Docker Hub username in both:
- `initContainers.image`
- `containers.image`

## Step 4: Deploy to Kubernetes

```bash
# Apply manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# Deploy PostgreSQL
kubectl apply -f k8s/postgres/

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n vc-diligence --timeout=120s

# Verify PostgreSQL is running
kubectl get pods -n vc-diligence -l app=postgres

# Deploy backend
kubectl apply -f k8s/backend/

# Wait for backend to be ready
kubectl wait --for=condition=ready pod -l app=backend -n vc-diligence --timeout=180s

# Deploy ingress
kubectl apply -f k8s/ingress/

# Check deployment status
kubectl get all -n vc-diligence
kubectl get ingress -n vc-diligence
```

## Step 5: Configure DNS

### For Local Testing (without SSL)

Add to `/etc/hosts`:
```bash
echo "127.0.0.1 vc.baisoln.com" | sudo tee -a /etc/hosts
```

### For Production with Let's Encrypt SSL

1. Get Kong ingress external IP:
```bash
kubectl get svc -n kong
```

2. Configure DNS A record:
   - Domain: vc.baisoln.com
   - Type: A
   - Value: <Kong-External-IP>

3. Verify DNS resolution:
```bash
nslookup vc.baisoln.com
```

4. Check certificate status:
```bash
kubectl get certificate -n vc-diligence
kubectl describe certificate vc-diligence-tls -n vc-diligence

# Wait for certificate to be ready (1-2 minutes)
kubectl wait --for=condition=ready certificate/vc-diligence-tls -n vc-diligence --timeout=300s
```

## Step 6: Verify Deployment

### Check Pods
```bash
kubectl get pods -n vc-diligence

# Expected output:
# NAME                        READY   STATUS    RESTARTS   AGE
# backend-xxx                 1/1     Running   0          2m
# backend-yyy                 1/1     Running   0          2m
# postgres-zzz                1/1     Running   0          5m
```

### Check Logs
```bash
# Backend logs
kubectl logs -n vc-diligence -l app=backend --tail=50

# PostgreSQL logs
kubectl logs -n vc-diligence -l app=postgres --tail=50
```

### Test Backend Health
```bash
# Port-forward for local testing
kubectl port-forward -n vc-diligence svc/backend-service 8000:8000

# In another terminal, test health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {"status":"healthy","timestamp":"2026-02-04T...","service":"vc-diligence-api"}
```

### Test via Ingress
```bash
# Test API health (HTTPS)
curl https://vc.baisoln.com/api/health

# Test API docs
open https://vc.baisoln.com/api/docs
```

## Step 7: Test Due Diligence API

### Trigger Research
```bash
curl -X POST https://vc.baisoln.com/api/research/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Agno AI",
    "company_url": "https://agno.com"
  }'

# Response:
# {
#   "success": true,
#   "message": "Research started successfully",
#   "task_id": "550e8400-e29b-41d4-a716-446655440000"
# }
```

### Check Status
```bash
TASK_ID="<task_id_from_above>"

curl https://vc.baisoln.com/api/research/status/$TASK_ID

# Response will show:
# - status: queued → in_progress → success
# - current_stage: Company Research → Market Analysis → etc.
# - artifacts: {chart, report, infographic} when completed
```

### Download Artifacts
```bash
# After task completes, download artifacts
curl https://vc.baisoln.com/api/research/artifact/$TASK_ID/revenue_chart_*.png -o chart.png
curl https://vc.baisoln.com/api/research/artifact/$TASK_ID/investment_report_*.html -o report.html
curl https://vc.baisoln.com/api/research/artifact/$TASK_ID/infographic_*.png -o infographic.png

# Open report in browser
open report.html
```

## Troubleshooting

### Backend Pods Not Starting

**Issue**: Backend pods in CrashLoopBackOff

**Solution**:
```bash
# Check pod logs
kubectl logs -n vc-diligence -l app=backend --tail=100

# Common issues:
# 1. Database connection failed - verify PostgreSQL is running
# 2. Missing GOOGLE_API_KEY - check secret is applied
# 3. Migration failed - check init container logs
kubectl logs -n vc-diligence <backend-pod> -c migration
```

### PostgreSQL Connection Failed

**Issue**: Backend can't connect to PostgreSQL

**Solution**:
```bash
# Check PostgreSQL pod
kubectl get pods -n vc-diligence -l app=postgres

# Test DNS resolution
kubectl run -n vc-diligence test-pod --image=busybox:1.28 --rm -it -- nslookup postgres-service

# Test connection from backend pod
kubectl exec -n vc-diligence <backend-pod> -- nc -zv postgres-service 5432
```

### PVC Not Binding

**Issue**: artifacts-pvc in Pending state

**Solution**:
```bash
# Check PVC status
kubectl get pvc -n vc-diligence

# Check if storage class supports ReadWriteMany
kubectl get storageclass

# If standard doesn't support ReadWriteMany:
# Option 1: Edit k8s/backend/pvc.yaml to use ReadWriteOnce and set backend replicas to 1
# Option 2: Deploy NFS server for shared storage
```

### Cert-manager Certificate Fails

**Issue**: Certificate stuck in Pending

**Solution**:
```bash
# Check certificate status
kubectl describe certificate vc-diligence-tls -n vc-diligence

# Common issues:
# 1. DNS not propagated - wait and check nslookup
# 2. Port 80/443 not accessible - check firewall
# 3. ClusterIssuer missing - verify cert-manager setup

# Check ClusterIssuer
kubectl get clusterissuer

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager
```

### Kong Ingress Not Routing

**Issue**: 404 or connection refused from vc.baisoln.com

**Solution**:
```bash
# Check ingress status
kubectl describe ingress -n vc-diligence vc-diligence-ingress

# Check Kong controller logs
kubectl logs -n kong -l app=ingress-kong --tail=100

# Verify backend service
kubectl get svc -n vc-diligence backend-service

# Test backend directly (port-forward)
kubectl port-forward -n vc-diligence svc/backend-service 8000:8000
curl http://localhost:8000/api/health
```

## Accessing the Application

### API Endpoints

- **Health Check**: https://vc.baisoln.com/api/health
- **API Documentation**: https://vc.baisoln.com/api/docs
- **Trigger Research**: POST https://vc.baisoln.com/api/research/trigger
- **Check Status**: GET https://vc.baisoln.com/api/research/status/{task_id}
- **Download Artifact**: GET https://vc.baisoln.com/api/research/artifact/{task_id}/{filename}
- **Research History**: GET https://vc.baisoln.com/api/research/history

### Example Workflow

1. **Start Research**:
   - Send POST request with company name/URL
   - Receive task_id

2. **Monitor Progress**:
   - Poll status endpoint every 3-5 seconds
   - Watch current_stage progress through 7 agents

3. **Retrieve Results**:
   - When status = "success", download artifacts
   - View HTML report, charts, infographic

## Updating the Deployment

### Update Backend Code

```bash
# Rebuild and push image
docker build -t your-dockerhub-username/vc-diligence-backend:latest -f backend/Dockerfile .
docker push your-dockerhub-username/vc-diligence-backend:latest

# Restart backend pods
kubectl rollout restart deployment/backend -n vc-diligence

# Watch rollout
kubectl rollout status deployment/backend -n vc-diligence
```

### Update Configuration

```bash
# Edit configmap or secret
kubectl edit configmap vc-diligence-config -n vc-diligence
kubectl edit secret vc-diligence-secrets -n vc-diligence

# Restart pods to pick up changes
kubectl rollout restart deployment/backend -n vc-diligence
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace vc-diligence

# Or delete individually
kubectl delete -f k8s/ingress/
kubectl delete -f k8s/backend/
kubectl delete -f k8s/postgres/
kubectl delete -f k8s/secret.yaml
kubectl delete -f k8s/configmap.yaml
kubectl delete -f k8s/namespace.yaml
```

## Next Steps

### Add Frontend (Optional)

The backend API is fully functional. You can:
1. Access it directly via API calls (curl, Postman)
2. Build a custom frontend (React, Next.js, etc.)
3. Use the API documentation at https://vc.baisoln.com/api/docs

### Production Enhancements

1. **Authentication**: Add API key or OAuth
2. **Monitoring**: Install Prometheus + Grafana
3. **Logging**: Set up ELK stack or Loki
4. **Backup**: Configure automated database backups
5. **Scaling**: Add HorizontalPodAutoscaler
6. **Storage**: Migrate to S3-compatible storage (MinIO/AWS S3)

## Support

For issues or questions:
- Check logs: `kubectl logs -n vc-diligence -l app=backend`
- Verify status: `kubectl get all -n vc-diligence`
- Review plan: See `/root/.claude/plans/jolly-floating-raven.md`

## Success Criteria

✅ Backend pods running (2 replicas)
✅ PostgreSQL pod running
✅ Health endpoint responding
✅ SSL certificate issued (if using Let's Encrypt)
✅ Can trigger research via API
✅ Can monitor status
✅ Can download artifacts
✅ All 7 agent stages execute successfully
