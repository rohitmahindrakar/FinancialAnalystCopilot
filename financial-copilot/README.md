# Financial Analyst Copilot

This repository contains a reorganized deployment-ready structure for Rancher and Kubernetes.

## Components

- `api/` — FastAPI backend that exposes finance, orchestrator, and intent APIs.
- `ui/` — Streamlit-based frontend for user interaction.
- `rag-service/` — Dedicated Chroma retrieval service for document search and vector store access.
- `ingestion-worker/` — Background document ingestion worker for chunking and storing data in Chroma.
- `k8s/` — Kubernetes manifests for each component plus storage and config.

## Build and run locally

From the workspace root:

- API: `python -m uvicorn services.api_app:app --reload`
- UI: `python -m streamlit run scripts/streamlit_app.py`
- Ingestion worker: `python -m services.rag.injest`

## Container build reference

- `financial-copilot/api/Containerfile`
- `financial-copilot/ui/Containerfile`
- `financial-copilot/rag-service/Containerfile`
- `financial-copilot/ingestion-worker/Containerfile`

## Kubernetes deployment

Apply manifests from `financial-copilot/k8s/` in Rancher or kubectl:

```bash
kubectl apply -f financial-copilot/k8s/configmap.yaml
kubectl apply -f financial-copilot/k8s/persistent-storage.yaml
kubectl apply -f financial-copilot/k8s/api.yaml
kubectl apply -f financial-copilot/k8s/ui.yaml
kubectl apply -f financial-copilot/k8s/rag-service.yaml
kubectl apply -f financial-copilot/k8s/ingestion-worker.yaml
```

## Notes

- The `financial-copilot` components reference the top-level repository code using Python `sys.path` adjustments.
- Update `k8s/configmap.yaml` with real secrets and environment values for production.
- Use a shared PVC for database and Chroma persistence if running both API and RAG services in the same cluster.
