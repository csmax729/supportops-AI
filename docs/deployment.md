# Deployment

Follow the local quick start in README first. For Docker, initialize .env, set the provider variables, then run the following from the repository root.

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://127.0.0.1:8000/ready
docker compose exec api python -m scripts.operator ingest
docker compose exec api python -m scripts.operator seed
docker compose logs --tail 40 api
docker compose down
```

The UI calls http://api:8000 inside Compose. The named volume retains SQLite, Chroma and cached models. Stop the service before snapshotting the entire volume so the relational catalog and vector data stay consistent. An ordinary compose down preserves this volume. On Docker Desktop the API reaches a host Ollama daemon via host.docker.internal. Configure the daemon to listen on an interface reachable by Docker and firewall it to trusted clients. Set CONTAINER_OLLAMA_URL for an alternate address. For llama.cpp set LLAMA_URL in .env to its container-reachable address.

Use a CPU VM with durable local disk and a single API worker for a small public demonstration behind an authenticated HTTPS gateway. Size RAM and disk using the actual model and dependency image, especially Torch on Linux. A hosted provider avoids local chat weights but charges for input and output according to the selected model. A sleeping free service incurs model-loading cold starts and ephemeral storage can erase tickets and indexes. No public deployment or ongoing hosting cost is assumed.
