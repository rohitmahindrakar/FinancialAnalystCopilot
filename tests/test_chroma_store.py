import importlib
from pathlib import Path


def test_chroma_store_tokenizes_and_persists_chunks(tmp_path):
    module = importlib.import_module("services.rag.chroma_store")
    store_cls = getattr(module, "ChunkChromaStore")

    store = store_cls(persist_directory=tmp_path / "chroma", collection_name="test_chunks")
    chunks = [
        module.ChunkRecord(
            document_name="doc.txt",
            chunk_index=0,
            chunk_text="Alpha beta gamma",
            word_count=3,
            headline="Intro",
            summary="A summary",
        )
    ]

    store.save_chunks(chunks)
    results = store.search("alpha", n_results=3)

    assert len(results["documents"]) == 1
    assert results["documents"][0] == "Alpha beta gamma"
    assert store.tokenize_chunk("Alpha beta gamma") == ["alpha", "beta", "gamma"]


def test_embedding_analyzer_recovers_from_corrupt_chroma_collection(monkeypatch, tmp_path):
    import services.rag.visualization as visualization_module

    class FakeCollection:
        def __init__(self):
            self.calls = 0

        def get(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Error creating hnsw segment reader: Nothing found on disk")
            return {
                "ids": ["1"],
                "documents": ["doc"],
                "metadatas": [{"source": "test"}],
                "embeddings": [[0.1, 0.2]],
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            self._attempts = 0
            self._collection = FakeCollection()

        def list_collections(self):
            return []

        def get_collection(self, name):
            raise RuntimeError("Error creating hnsw segment reader: Nothing found on disk")

        def get_or_create_collection(self, name, metadata=None):
            self._attempts += 1
            if self._attempts == 1:
                raise RuntimeError("Error creating hnsw segment reader: Nothing found on disk")
            return self._collection

        def delete_collection(self, name):
            return None

    monkeypatch.setattr(visualization_module, "PersistentClient", lambda *args, **kwargs: FakeClient(*args, **kwargs))

    analyzer = visualization_module.ChunkEmbeddingAnalyzer(
        persist_directory=tmp_path / "database" / "chroma",
        collection_name="sample_docs_chunks",
    )
    records = analyzer.get_collection_data()

    assert len(records) == 1
    assert records[0]["document"] == "doc"
