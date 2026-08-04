import importlib
from pathlib import Path


def test_injestor_uses_repo_root_for_chroma_persistence(tmp_path):
    repo_root = tmp_path / "repo"
    source_dir = repo_root / "notebooks" / "sample_docs"
    source_dir.mkdir(parents=True)
    (repo_root / "services").mkdir()
    (repo_root / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    module = importlib.import_module("services.rag.injest")
    ingestor = module.Injestor(source_dir=source_dir, model="dummy", provider="ollama")

    assert ingestor.chroma_store.persist_directory == repo_root / "database" / "chroma"
