import importlib


def test_import_rag_ingestor_without_api_dependencies():
    services = importlib.import_module("services")
    assert services is not None

    rag_module = importlib.import_module("services.rag.injest")
    assert getattr(rag_module, "Injestor", None) is not None
