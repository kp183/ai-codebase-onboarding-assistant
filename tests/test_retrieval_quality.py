import asyncio
import sys
from datetime import datetime
from types import SimpleNamespace

from app.models.data_models import CodeChunk, EmbeddedChunk
from app.services import embedding_service as embedding_module
from app.services import search_service as search_module
from app.services.query_processing import QueryProcessingService
from app.services.search_service import SearchService, SearchResult


def test_local_model_embedding_includes_file_path(monkeypatch):
    from app.config import settings

    captured = {}

    class FakeVector(list):
        def tolist(self):
            return list(self)

    class FakeTextEmbedding:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name

        def embed(self, texts, **kwargs):
            captured["texts"] = texts
            return [FakeVector([0.1, 0.2]) for _ in texts]

    monkeypatch.setitem(
        sys.modules, "fastembed", SimpleNamespace(TextEmbedding=FakeTextEmbedding)
    )
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "local_embeddings", True)
    monkeypatch.setattr(settings, "local_embedding_model", "test-model")

    chunk = CodeChunk(
        id="chunk",
        repo_id="repo",
        file_path="src/cart.py",
        content="def total(): return sum(items)",
        start_line=1,
        end_line=1,
        language="python",
        chunk_type="function",
    )
    service = embedding_module.EmbeddingService()
    embedded = asyncio.run(service.generate_embeddings([chunk]))

    assert captured["texts"] == ["File path: src/cart.py\ndef total(): return sum(items)"]
    assert captured["model_name"] == "test-model"
    assert embedded[0].embedding == [0.1, 0.2]


def test_local_bm25_uses_repository_content_and_file_paths(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(search_module, "_LOCAL_DOCUMENTS", {})
    service = SearchService()
    expected = CodeChunk(
        id="a",
        repo_id="repo",
        file_path="src/flask/sansio/scaffold.py",
        content="The route decorator adds a URL rule for a view function.",
        start_line=1,
        end_line=1,
        language="python",
        chunk_type="function",
    )
    distractor = CodeChunk(
        id="b",
        repo_id="repo",
        file_path="src/flask/templating.py",
        content="Render a template with the provided context.",
        start_line=1,
        end_line=1,
        language="python",
        chunk_type="function",
    )
    service.store_embeddings(
        [
            EmbeddedChunk(
                chunk=expected, embedding=[], embedding_model="bm25-only", created_at=datetime.utcnow()
            ),
            EmbeddedChunk(
                chunk=distractor, embedding=[], embedding_model="bm25-only", created_at=datetime.utcnow()
            ),
        ]
    )

    results = service.vector_search(
        query_embedding=[],
        query_text="Which decorator connects a URL to a view function?",
        repo_id="repo",
    )
    assert results[0].chunk.file_path == "src/flask/sansio/scaffold.py"


def test_demo_not_found_uses_score_threshold_not_exact_term_match(monkeypatch):
    from app.config import settings

    chunk = CodeChunk(
        id="chunk",
        repo_id="repo",
        file_path="src/flask/app.py",
        content="def dispatch_request(self): return self.view_functions[rule.endpoint]()",
        start_line=10,
        end_line=12,
        language="python",
        chunk_type="function",
    )
    service = QueryProcessingService.__new__(QueryProcessingService)
    service.local_mode = True
    service._initialized = True
    service.embedding_service = SimpleNamespace(use_local_embeddings=True)
    monkeypatch.setattr(settings, "demo_mode", True)

    async def retrieve(question, top_k, repo_id=None):
        return [SearchResult(chunk, 0.42)]

    service.retrieve_relevant_chunks = retrieve
    response = asyncio.run(
        service.process_query("Where does an incoming call get routed?", repo_id="repo")
    )
    assert "Not found in repo" not in response.answer
    assert response.sources[0].file_path == "src/flask/app.py"


def test_demo_not_found_threshold_rejects_weak_results():
    chunk = CodeChunk(
        id="chunk",
        repo_id="repo",
        file_path="src/flask/app.py",
        content="def dispatch_request(self): pass",
        start_line=1,
        end_line=1,
        language="python",
        chunk_type="function",
    )
    service = QueryProcessingService.__new__(QueryProcessingService)
    service.local_mode = True
    service._initialized = True
    service.embedding_service = SimpleNamespace(use_local_embeddings=True)

    async def retrieve(question, top_k, repo_id=None):
        return [SearchResult(chunk, 0.05)]

    service.retrieve_relevant_chunks = retrieve
    response = asyncio.run(service.process_query("Tell me about the deployment", repo_id="repo"))
    assert "Not found in repo" in response.answer


def test_demo_not_found_threshold_rejects_unrelated_midrange_match():
    chunk = CodeChunk(
        id="chunk",
        repo_id="repo",
        file_path="src/werkzeug/security.py",
        content="def generate_password_hash(password): pass",
        start_line=1,
        end_line=1,
        language="python",
        chunk_type="function",
    )
    service = QueryProcessingService.__new__(QueryProcessingService)
    service.local_mode = True
    service._initialized = True
    service.embedding_service = SimpleNamespace(use_local_embeddings=True)

    async def retrieve(question, top_k, repo_id=None):
        return [SearchResult(chunk, 0.30)]

    service.retrieve_relevant_chunks = retrieve
    response = asyncio.run(
        service.process_query(
            "How does it send password reset emails through SendGrid?", repo_id="repo"
        )
    )
    assert "Not found in repo" in response.answer


def test_demo_not_found_uses_average_of_top_three_scores():
    chunks = [
        CodeChunk(
            id=f"chunk-{index}",
            repo_id="repo",
            file_path=f"src/file_{index}.py",
            content="unrelated result",
            start_line=1,
            end_line=1,
            language="python",
            chunk_type="function",
        )
        for index in range(3)
    ]
    service = QueryProcessingService.__new__(QueryProcessingService)
    service.local_mode = True
    service._initialized = True
    service.embedding_service = SimpleNamespace(use_local_embeddings=True)

    async def retrieve(question, top_k, repo_id=None):
        return [
            SearchResult(chunks[0], 0.80),
            SearchResult(chunks[1], 0.10),
            SearchResult(chunks[2], 0.10),
        ]

    service.retrieve_relevant_chunks = retrieve
    response = asyncio.run(
        service.process_query("Where is a fictional feature implemented?", repo_id="repo")
    )
    assert "Not found in repo" in response.answer
