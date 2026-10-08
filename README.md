# AI Codebase Onboarding Assistant

A small FastAPI application for ingesting a repository and asking questions with retrieved code snippets and file/line citations.

## Local demo (no Azure credentials)

Verified Python: 3.11, 3.12, and 3.13 on Windows with a clean dependency install and the default test suite.

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python run_dev.py
```

Open http://127.0.0.1:8002. The included `tests/fixtures/sample_repo` can be ingested through `POST /api/ingest` by passing its absolute local path as `repository_url` in demo mode. The browser UI accepts public GitHub HTTPS URLs. After ingesting, ask about symbols or behavior in the repository.

Demo mode uses an in-memory store and BM25-style keyword retrieval by default. For local semantic embeddings, install `requirements-local.txt`, set `LOCAL_EMBEDDINGS=true`, and restart. FastEmbed downloads the selected model the first time it runs; inference then runs locally. Retrieved snippets are returned as a clearly labeled retrieval-only answer, with “Not found in repo” when the best relevance score is below the guard threshold. Data is lost when the process stops. This is a local demo, not a multi-user or private-repository deployment.

## What is implemented

- Public GitHub repository clone, source filtering, chunking, BM25 retrieval, and optional local semantic embeddings.
- Local fixture ingestion and retrieval without Azure credentials when `DEMO_MODE=true`.
- Browser form for repository ingestion and chat with source file/line references.

## Not implemented / limitations

- Azure mode requires configured Azure OpenAI and Azure AI Search resources; it has not been validated here.
- Local semantic embeddings are optional and require a one-time model download; without them, demo retrieval uses BM25-style keyword scoring. The demo returns retrieved snippets and does not generate explanations.
- No authentication, tenant isolation, persistent local index, background jobs, or production deployment controls.
- The local demo only permits ingesting the checked-in fixture path. The browser flow ingests public GitHub HTTPS repositories.

## Tests

```powershell
python -m pytest
```

Azure integration tests are marked `azure` and skipped by default. Run them explicitly with `python -m pytest -m azure` only after configuring credentials.
