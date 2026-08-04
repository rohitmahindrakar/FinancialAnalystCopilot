import importlib


def test_refactored_rag_modules_are_available():
    models = importlib.import_module("services.rag.models")
    readers = importlib.import_module("services.rag.readers")
    providers = importlib.import_module("services.rag.providers")
    chunking = importlib.import_module("services.rag.chunking")

    assert hasattr(models, "ChunkRecord")
    assert hasattr(models, "IngestionResult")
    assert hasattr(readers, "DocumentReader")
    assert hasattr(providers, "ModelProvider")
    assert hasattr(chunking, "ChunkingHelper")
