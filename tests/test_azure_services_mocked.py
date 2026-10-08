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


def test_azure_delete_repository_pages_through_all_chunks(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    search_client = Mock()
    monkeypatch.setattr(search_module, "AzureKeyCredential", lambda key: "mock-credential")
    monkeypatch.setattr(search_module, "SearchIndexClient", lambda **kwargs: Mock())
    monkeypatch.setattr(search_module, "SearchClient", lambda **kwargs: search_client)
    search_client.search.side_effect = [
        [{"id": f"chunk-{index}"} for index in range(1000)],
        [{"id": f"chunk-{index}"} for index in range(1000, 2000)],
        [],
    ]
    search_client.delete_documents.return_value = [SimpleNamespace(succeeded=True)] * 1000

    assert search_module.SearchService().delete_repository("repo-a") is True
    assert [call.kwargs["skip"] for call in search_client.search.call_args_list] == [0, 1000, 2000]
    assert [len(call.args[0]) for call in search_client.delete_documents.call_args_list] == [1000, 1000]


def test_existing_azure_index_gets_filterable_repo_id_field(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False)
    index_client = Mock()
    monkeypatch.setattr(search_module, "AzureKeyCredential", lambda key: "mock-credential")
    monkeypatch.setattr(search_module, "SearchIndexClient", lambda **kwargs: index_client)
    monkeypatch.setattr(search_module, "SearchClient", lambda **kwargs: Mock())
    existing_index = SimpleNamespace(fields=[])
    index_client.get_index.return_value = existing_index

    assert search_module.SearchService().index_exists() is True
    assert existing_index.fields[0].name == "repo_id"
    assert existing_index.fields[0].filterable is True
    index_client.create_or_update_index.assert_called_once_with(existing_index)


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
        input=["File path: src/main.py\ndef main(): pass"],
        model=settings.azure_openai_embedding_deployment,
    )
