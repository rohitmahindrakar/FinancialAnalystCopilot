from __future__ import annotations

import logging
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


class DocumentReader:
    """Read supported document formats into plain text."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self.logger = logger or logging.getLogger(__name__)
        self.supported_extensions = {
            ".txt",
            ".md",
            ".json",
            ".csv",
            ".html",
            ".xml",
            ".yaml",
            ".yml",
            ".pdf",
            ".doc",
            ".docx",
        }

    def list_documents(self, source_dir: Path) -> list[Path]:
        return sorted(
            path
            for path in source_dir.iterdir()
            if path.is_file() and path.suffix.lower() in self.supported_extensions
        )

    def read_text(self, path: Path) -> str:
        """Read plain-text-like documents including PDF and Word files when available."""
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            try:
                from pypdf import PdfReader  # type: ignore[import-not-found]
            except ImportError as exc:  # pragma: no cover - import guard
                self.logger.warning("PDF support requires pypdf. Install it to ingest PDF files.")
                raise RuntimeError("PDF support requires pypdf. Install it to ingest PDF files.") from exc

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n\n".join(page for page in pages if page)

        if suffix == ".doc":
            try:
                completed = subprocess.run(
                    ["antiword", str(path)],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                return completed.stdout.strip()
            except (FileNotFoundError, subprocess.CalledProcessError) as exc:  # pragma: no cover - import guard
                raise RuntimeError("DOC support requires antiword to be installed and available on PATH.") from exc

        if suffix == ".docx":
            try:
                from docx import Document  # type: ignore[import-not-found]
            except ImportError:
                return self._read_docx_with_zipfile(path)

            document = Document(str(path))
            paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
            return "\n\n".join(paragraphs)

        if suffix in {".txt", ".md", ".json", ".csv", ".html", ".xml", ".yaml", ".yml"}:
            return path.read_text(encoding="utf-8", errors="ignore")

        raise RuntimeError(f"Unsupported document type: {path.suffix}")

    def _read_docx_with_zipfile(self, path: Path) -> str:
        """Read text from a .docx file using the standard library when python-docx is unavailable."""
        try:
            with zipfile.ZipFile(path) as docx_zip:
                xml_data = docx_zip.read("word/document.xml")
        except (FileNotFoundError, KeyError, zipfile.BadZipFile) as exc:
            raise RuntimeError("Unable to read DOCX file contents.") from exc

        root = ET.fromstring(xml_data)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []

        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            paragraph_text = "".join(texts).strip()
            if paragraph_text:
                paragraphs.append(paragraph_text)

        return "\n\n".join(paragraphs)


__all__ = ["DocumentReader"]
