# Contract360 — Deploy Runbook (Azure Container Apps via Cloud Shell)

Tested path: **Windows → Azure Cloud Shell (Bash)**. No local Docker needed —
images build in the cloud via `az acr build`.

---

## 0. One-time prerequisites (per Azure subscription)

- A **Pay-As-You-Go** subscription (the free trial blocks ACR Tasks / cloud builds).
- Your data services already provisioned: Azure OpenAI, Azure AI Search,
  Blob Storage, Cosmos DB (NoSQL), optionally Cosmos Gremlin.

Register the required resource providers (only needed once per subscription):

```bash
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.ContainerService
# Wait until each shows "Registered":
az provider show --namespace Microsoft.App --query registrationState -o tsv
```

---

## 1. Prepare `.env` (on your PC)

- Copy `.env.example` → `.env` and fill in every REQUIRED value.
- **Quote the blob connection string** (it has semicolons):
  ```
  AZURE_BLOB_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
  ```
- Make sure deployment names match your Azure OpenAI Studio exactly
  (`AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`).
- Demo-safe flags (already default to true in the deploy script):
  ```
  DISABLE_KG_EXTRACTION=true     # fast tree-only ingestion, no rate limits
  DISABLE_GRAPH_ROUTE=true       # deterministic tree-only answering
  JOB_STALE_AFTER_MINUTES=15     # no stuck upload spinners
  ```
- Save as LF line endings (not CRLF). Keep `GREMLIN_*` populated only if you
  want graph features later.

---

## 2. Zip the project (include these)

```
deploy-aca.sh  Dockerfile  .dockerignore  requirements.txt  .env
app/  frontend/   (frontend WITHOUT node_modules and dist)
```
Skip `data/`, `docs/`, `tests/`. Enable "show hidden files" so `.env` is included.

---

## 3. Cloud Shell

1. Open https://shell.azure.com → choose **Bash** → **No storage account (ephemeral)** is fine.
2. Confirm subscription:
   ```bash
   az account show --query name -o tsv
   az account set --subscription "<your-subscription-name>"   # if needed
   ```
3. Upload the zip (toolbar → Upload), then:
   ```bash
   unzip rag_system.zip
   cd "<folder-containing-deploy-aca.sh>"
   sed -i 's/\r$//' deploy-aca.sh .env     # strip any CRLF from Windows
   cat .env | head -5                      # sanity-check it uploaded
   ```

---

## 4. Deploy

```bash
export ACR_NAME="contract360acr$RANDOM"   # must be globally unique, lowercase
export LOCATION="eastus"                   # near your data services
chmod +x deploy-aca.sh
./deploy-aca.sh
```
Takes ~10–15 min. Prints the Frontend + Backend URLs at the end. Re-runnable
(idempotent) if it fails partway.

---

## 5. Verify

```bash
curl -i https://<api-url>/health        # expect 200
az containerapp logs show -n contract360-api -g contract360-rg --tail 100
```
Then open the Frontend URL, upload a demo PDF, and ask a question.

---

## 6. Redeploy after code changes

Just re-upload the changed files (or re-zip) and run `./deploy-aca.sh` again.
The pip/npm layers are cached, so it's faster. Env-only changes can instead use:
```bash
az containerapp update -n contract360-api -g contract360-rg \
  --set-env-vars DISABLE_GRAPH_ROUTE=true
```

---

## 7. Stop / tear down (to stop billing)

```bash
# Park it (cheapest, keeps everything):
az containerapp update -n contract360-api -g contract360-rg --min-replicas 0
az containerapp update -n contract360-ui  -g contract360-rg --min-replicas 0

# Full teardown of the compute group (verify first it has no data services!):
az resource list -g contract360-rg -o table
az group delete --name contract360-rg --yes --no-wait
az group exists --name contract360-rg     # false = deleted
```

---

## Gotchas we hit (and fixes)

| Symptom | Cause | Fix |
|---|---|---|
| `COSMOS_NOSQL_ENDPOINT: command not found` | space around `=` or CRLF in `.env` | no spaces around `=`; `sed -i 's/\r$//' .env` |
| `ACR Tasks not permitted` | free-trial subscription | upgrade to Pay-As-You-Go |
| `COPY .env*` build fail | `.env` excluded by `.dockerignore` | (already removed from Dockerfile) |
| `COPY nginx.conf` build fail | `nginx.conf` listed in `frontend/.dockerignore` | (already removed) |
| `KeyError: ACCOUNTNAME` at startup | blob conn string truncated by `;` | wrap value in double quotes in `.env` |
| `python-multipart not installed` | missing dep | (already added to requirements.txt) |
| Cosmos header spam in logs | Azure SDK INFO logs | (already silenced in api.py) |
