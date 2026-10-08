from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.config import settings
from app.models.data_models import CodeChunk, EmbeddedChunk
from app.services import embedding_service as embedding_module
from app.services import search_service as search_module


def test_azure_search_mode_scopes_upload_search_and_delete(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    index_client = Mock()
    search_client = Mock()
    monkeypatch.setattr(search_module, "AzureKeyCredential", lambda key: "mock-credential")
    monkeypatch.setattr(search_module, "SearchIndexClient", lambda **kwargs: index_client)
    monkeypatch.setattr(search_module, "SearchClient", lambda **kwargs: search_client)

    service = search_module.SearchService()
    assert service.local_mode is False
    chunk = CodeChunk(
        id="chunk-a",
        repo_id="repo-a",
        file_path="src/main.py",
        content="def main(): pass",
        start_line=1,
        end_line=1,
        language="python",
    )
    embedded = EmbeddedChunk(
        chunk=chunk,
        embedding=[0.1] * 1536,
        embedding_model="mock-embedding",
        created_at=datetime.utcnow(),
    )
    search_client.upload_documents.return_value = [SimpleNamespace(succeeded=True)]
    assert service.store_embeddings([embedded]) is True
    uploaded = search_client.upload_documents.call_args.args[0]
    assert uploaded[0]["repo_id"] == "repo-a"

    search_client.search.return_value = [
        {
            "id": "chunk-a",
            "repo_id": "repo-a",
            "content": "def main(): pass",
            "file_path": "src/main.py",
            "start_line": 1,
            "end_line": 1,
            "language": "python",
            "chunk_type": "function",
            "@search.score": 0.9,
        }
    ]
    results = service.vector_search([0.1] * 1536, repo_id="repo-a")
    assert results[0].chunk.repo_id == "repo-a"
    assert search_client.search.call_args.kwargs["filter"] == "repo_id eq 'repo-a'"

    search_client.search.return_value = [{"id": "chunk-a"}]
    search_client.delete_documents.return_value = [SimpleNamespace(succeeded=True)]
    assert service.delete_repository("repo-a") is True
    assert search_client.search.call_args.kwargs["filter"] == "repo_id eq 'repo-a'"
    assert search_client.delete_documents.call_args.args[0] == [{"id": "chunk-a"}]

    service.create_index()
    fields = index_client.create_index.call_args.args[0].fields
    assert any(field.name == "repo_id" and field.filterable for field in fields)


@pytest.mark.asyncio
async def test_azure_embedding_mode_calls_mocked_client(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    client = AsyncMock()
    client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.25] * 1536)]
    )
    constructor = Mock(return_value=client)
    monkeypatch.setattr(embedding_module, "AsyncAzureOpenAI", constructor)

    service = embedding_module.EmbeddingService()
    chunk = CodeChunk(
        id="azure-mock-chunk",
        repo_id="repo-a",
        file_path="src/main.py",
        content="def main(): pass",
        start_line=1,
        end_line=1,
        language="python",
    )
    embedded = await service.generate_embeddings([chunk])

    assert service.local_mode is False
    assert constructor.called
    assert len(embedded) == 1
    assert embedded[0].embedding == [0.25] * 1536
    client.embeddings.create.assert_awaited_once_with(
        input=["def main(): pass"], model=settings.azure_openai_embedding_deployment
    )
