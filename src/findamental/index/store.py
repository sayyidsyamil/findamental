from pathlib import Path

from findamental.config import settings
from findamental.index.models import IndexedDocument
from findamental.index.pack import DocumentPackBuilder
from findamental.index.pymupdf_indexer import PyMuPDFDocumentIndexer


class DocumentIndexStore:
    def __init__(self, index_dir: Path | None = None):
        self.index_dir = index_dir or (settings.DATA_DIR / "document_index")
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, document_id: str) -> Path:
        return self.index_dir / f"{document_id}.json"

    def load(self, document_id: str) -> IndexedDocument | None:
        path = self.path_for(document_id)
        if not path.exists():
            return None
        return IndexedDocument.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, document: IndexedDocument) -> Path:
        path = document.save(self.path_for(document.document_id))
        DocumentPackBuilder(settings.DATA_DIR / "document_pack").build(document)
        return path

    def ensure_pdf_index(
        self,
        pdf_path: Path,
        ticker: str,
        company_name: str,
        document_id: str,
    ) -> IndexedDocument:
        existing = self.load(document_id)
        index_path = self.path_for(document_id)
        if existing and index_path.stat().st_mtime >= pdf_path.stat().st_mtime:
            return existing
        document = PyMuPDFDocumentIndexer().index_pdf(pdf_path, ticker, company_name, document_id)
        self.save(document)
        return document
