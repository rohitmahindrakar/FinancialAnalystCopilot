from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

import numpy as np

from chromadb import PersistentClient
from chromadb.config import Settings


def _default_chroma_persist_directory(repo_root: Optional[str | Path] = None) -> Path:
    root = Path(repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    return root / "database" / "chroma"


class ChunkEmbeddingAnalyzer:
    """Inspect and visualize embeddings stored in a Chroma collection."""

    def __init__(
        self,
        persist_directory: Optional[str | Path] = None,
        collection_name: str = "financial_chunks",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.persist_directory = Path(persist_directory or _default_chroma_persist_directory()).expanduser()
        self.collection_name = collection_name
        self.logger = logger or logging.getLogger(__name__)
        self._client = PersistentClient(path=str(self.persist_directory), settings=Settings(anonymized_telemetry=False))
        self._connect_collection()

    def _is_recoverable_chroma_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return "nothing found on disk" in message or "segment reader" in message or "hnsw" in message or "collection" in message and "not found" in message

    def _reset_collection(self) -> None:
        self.logger.warning("Chroma collection '%s' is unreadable; recreating it in '%s'", self.collection_name, self.persist_directory)
        try:
            self._client.delete_collection(self.collection_name)
        except Exception as delete_exc:
            self.logger.warning("Unable to delete Chroma collection '%s': %s", self.collection_name, delete_exc)

        try:
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as create_exc:
            if self.persist_directory.exists():
                shutil.rmtree(self.persist_directory, ignore_errors=True)
                self.persist_directory.mkdir(parents=True, exist_ok=True)
                self._client = PersistentClient(path=str(self.persist_directory), settings=Settings(anonymized_telemetry=False))
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
            else:
                raise create_exc

    def _connect_collection(self) -> None:
        try:
            available_collections = [col.name for col in self._client.list_collections()]
        except Exception as list_exc:
            if self._is_recoverable_chroma_error(list_exc):
                self._reset_collection()
                return
            raise

        try:
            if self.collection_name in available_collections:
                self._collection = self._client.get_collection(name=self.collection_name)
            elif len(available_collections) == 1:
                self.collection_name = available_collections[0]
                self._collection = self._client.get_collection(name=self.collection_name)
            elif available_collections:
                fallback = next((name for name in available_collections if name.endswith("_chunks")), available_collections[0])
                self.collection_name = fallback
                self._collection = self._client.get_collection(name=self.collection_name)
            else:
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
        except Exception as connect_exc:
            if self._is_recoverable_chroma_error(connect_exc):
                self._reset_collection()
                return
            raise

    def _get_collection_data_with_recovery(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._collection.get(**kwargs)
        except Exception as exc:
            if self._is_recoverable_chroma_error(exc):
                self._reset_collection()
                return self._collection.get(**kwargs)
            raise

    def _normalize_collection_values(self, value: Any) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, np.ndarray):
            return value.tolist() if value.size > 0 else []
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    def get_collection_data(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """Fetch documents, metadata, and embeddings for the collection."""
        kwargs: dict[str, Any] = {"include": ["documents", "metadatas", "embeddings"]}
        if limit is not None:
            kwargs["limit"] = int(limit)

        print(f"Fetching data from Chroma collection '{self.collection_name}' with limit={limit}")

        result = self._get_collection_data_with_recovery(kwargs)
        ids = self._normalize_collection_values(result.get("ids", []))
        documents = self._normalize_collection_values(result.get("documents", []))
        metadatas = self._normalize_collection_values(result.get("metadatas", []))
        embeddings = self._normalize_collection_values(result.get("embeddings", []))
        print(f"Retrieved {len(ids)} records from Chroma collection '{self.collection_name}'")

        records: list[dict[str, Any]] = []
        for index, document in enumerate(documents):
            metadata = metadatas[index] if index < len(metadatas) else {}
            embedding = embeddings[index] if index < len(embeddings) else None
            records.append(
                {
                    "id": ids[index] if index < len(ids) else str(index),
                    "document": document,
                    "metadata": metadata or {},
                    "embedding": embedding,
                }
            )
        return records

    def _normalize_embedding(self, embedding: Any) -> Optional[np.ndarray]:
        if embedding is None:
            return None
        try:
            array = np.asarray(embedding, dtype=float)
        except (TypeError, ValueError):
            return None
        if array.size == 0:
            return None
        return array

    def _valid_records(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [record for record in records if self._normalize_embedding(record.get("embedding")) is not None]

    def build_summary(self, limit: Optional[int] = None) -> dict[str, Any]:
        """Create a compact summary of the stored embeddings."""
        records = self.get_collection_data(limit=limit)
        valid_records = self._valid_records(records)
        vectors = [self._normalize_embedding(record["embedding"]) for record in valid_records]
        if vectors:
            first_vector = vectors[0]
            shape = np.asarray(first_vector).shape
            embedding_dim = int(np.asarray(first_vector).size)
        else:
            shape = ()
            embedding_dim = None

        return {
            "collection_name": self.collection_name,
            "persist_directory": str(self.persist_directory),
            "record_count": len(records),
            "with_embeddings": len(vectors),
            "embedding_dim": embedding_dim,
            "embedding_shape": shape,
            "sample_documents": [record["document"] for record in valid_records[:5]],
        }

    def _prepare_vectors(self, records: list[dict[str, Any]], n_components: int) -> np.ndarray:
        valid_records = self._valid_records(records)
        if not valid_records:
            raise ValueError("No non-empty embeddings are available for visualization.")

        vectors = [self._normalize_embedding(record["embedding"]) for record in valid_records]
        matrix = np.vstack(vectors)
        if matrix.shape[1] < n_components:
            n_components = matrix.shape[1]
        if n_components <= 1:
            n_components = 2

        try:
            from sklearn.decomposition import PCA
        except Exception:
            PCA = None

        if PCA is not None and matrix.shape[0] >= 2 and matrix.shape[1] >= 2:
            reducer = PCA(n_components=n_components)
            return reducer.fit_transform(matrix)

        if n_components == 2:
            return matrix[:, :2]
        if n_components == 3:
            projected = matrix[:, :3]
            if projected.shape[1] < 3:
                padded = np.zeros((projected.shape[0], 3), dtype=float)
                padded[:, : projected.shape[1]] = projected
                return padded
            return projected
        return matrix[:, :n_components]

    def visualize(self, dimensions: int = 2, output_path: Optional[str | Path] = None, title: Optional[str] = None, show: bool = True) -> Any:
        """Visualize embeddings in 2D or 3D using Plotly, with a Matplotlib fallback."""
        if dimensions not in {2, 3}:
            raise ValueError("dimensions must be either 2 or 3")

        records = self.get_collection_data()
        if not records:
            raise ValueError("The Chroma collection does not contain any chunks to visualize.")

        valid_records = self._valid_records(records)
        if not valid_records:
            self.logger.warning("The Chroma collection '%s' does not contain any non-empty embeddings yet.", self.collection_name)
            return None

        projected = self._prepare_vectors(valid_records, n_components=dimensions)
        labels = [record["id"] for record in valid_records]
        documents = [record["document"] for record in valid_records]
        metadatas = [record["metadata"] for record in valid_records]

        try:
            import plotly.graph_objects as go

            if dimensions == 2:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=projected[:, 0],
                        y=projected[:, 1],
                        mode="markers+text",
                        text=labels,
                        textposition="top center",
                        hovertemplate=(
                            "ID: %{text}<br>"
                            "Document: %{customdata[0]}<br>"
                            "Metadata: %{customdata[1]}<extra></extra>"
                        ),
                        customdata=list(zip(documents, [str(meta) for meta in metadatas])),
                        marker={"size": 10, "opacity": 0.8},
                    )
                )
            else:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter3d(
                        x=projected[:, 0],
                        y=projected[:, 1],
                        z=projected[:, 2],
                        mode="markers+text",
                        text=labels,
                        textposition="top center",
                        hovertemplate=(
                            "ID: %{text}<br>"
                            "Document: %{customdata[0]}<br>"
                            "Metadata: %{customdata[1]}<extra></extra>"
                        ),
                        customdata=list(zip(documents, [str(meta) for meta in metadatas])),
                        marker={"size": 4, "opacity": 0.8},
                    )
                )

            fig.update_layout(
                title=title or f"Chunk embeddings ({dimensions}D)",
                template="plotly_white",
                margin={"l": 20, "r": 20, "t": 50, "b": 20},
            )
            if output_path is not None:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                fig.write_html(str(output_path))
            if show:
                fig.show()
            return fig
        except Exception as exc:
            self.logger.warning("Plotly visualization unavailable; falling back to Matplotlib: %s", exc)
            import matplotlib.pyplot as plt

            if dimensions == 2:
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.scatter(projected[:, 0], projected[:, 1], alpha=0.8)
                for point, label in zip(projected, labels):
                    ax.annotate(label, (point[0], point[1]), fontsize=7)
                ax.set_title(title or f"Chunk embeddings ({dimensions}D)")
                ax.set_xlabel("Component 1")
                ax.set_ylabel("Component 2")
            else:
                from mpl_toolkits import mplot3d  # noqa: F401

                fig = plt.figure(figsize=(8, 6))
                ax = fig.add_subplot(111, projection="3d")
                ax.scatter(projected[:, 0], projected[:, 1], projected[:, 2], alpha=0.8)
                for point, label in zip(projected, labels):
                    ax.text(point[0], point[1], point[2], label, fontsize=7)
                ax.set_title(title or f"Chunk embeddings ({dimensions}D)")
                ax.set_xlabel("Component 1")
                ax.set_ylabel("Component 2")
                ax.set_zlabel("Component 3")

            if output_path is not None:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                fig.savefig(output_path, dpi=200, bbox_inches="tight")
            if show:
                plt.show()
            return fig

    def visualize_2d(self, output_path: Optional[str | Path] = None, title: Optional[str] = None, show: bool = True) -> Any:
        return self.visualize(dimensions=2, output_path=output_path, title=title, show=show)

    def visualize_3d(self, output_path: Optional[str | Path] = None, title: Optional[str] = None, show: bool = True) -> Any:
        return self.visualize(dimensions=3, output_path=output_path, title=title, show=show)


__all__ = ["ChunkEmbeddingAnalyzer"]
