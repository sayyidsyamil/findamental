from pathlib import Path
import platform
from typing import Any


class DoclingExtractor:
    def __init__(self):
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import VlmPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        pipeline_opts = VlmPipelineOptions()
        if platform.system() == "Darwin" and platform.machine() == "arm64":
            pipeline_opts.vlm_options = "granite_docling"

        self.converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)}
        )

    def extract(self, pdf_path: Path) -> Any:
        result = self.converter.convert(str(pdf_path))
        return result.document

    def extract_tables_with_bboxes(self, pdf_path: Path) -> list[dict]:
        document = self.extract(pdf_path)
        tables = []
        for table in getattr(document, "tables", []) or []:
            rows = _extract_rows(table)
            bbox = _extract_bbox(table)
            page_number = _extract_page_number(table)
            tables.append(
                {
                    "page_number": page_number,
                    "bbox": bbox,
                    "rows": rows,
                    "headers": rows[0] if rows else [],
                }
            )
        return tables


def _extract_rows(table: Any) -> list[list[str]]:
    if hasattr(table, "export_to_dataframe"):
        try:
            frame = table.export_to_dataframe()
            return [list(map(str, frame.columns))] + [
                [str(value) for value in row] for row in frame.to_numpy().tolist()
            ]
        except Exception:
            pass

    data = getattr(table, "data", None)
    grid = getattr(data, "grid", None)
    if grid:
        return [[str(getattr(cell, "text", cell) or "") for cell in row] for row in grid]
    return []


def _extract_bbox(table: Any) -> tuple[float, float, float, float]:
    prov = (getattr(table, "prov", None) or [None])[0]
    bbox = getattr(prov, "bbox", None) or getattr(table, "bbox", None)
    if bbox is None:
        return (0.0, 0.0, 0.0, 0.0)
    left = float(getattr(bbox, "l", getattr(bbox, "left", 0.0)))
    top = float(getattr(bbox, "t", getattr(bbox, "top", 0.0)))
    right = float(getattr(bbox, "r", getattr(bbox, "right", 0.0)))
    bottom = float(getattr(bbox, "b", getattr(bbox, "bottom", 0.0)))
    return (left, top, right, bottom)


def _extract_page_number(table: Any) -> int:
    prov = (getattr(table, "prov", None) or [None])[0]
    return int(getattr(prov, "page_no", 1) or 1)
