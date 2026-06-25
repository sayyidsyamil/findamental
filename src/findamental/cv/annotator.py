from pathlib import Path

import fitz
from PIL import Image, ImageDraw


class PageAnnotator:
    def crop_and_annotate(
        self,
        pdf_path: Path,
        page_number: int,
        bbox: tuple[float, float, float, float],
        row_bbox: tuple[float, float, float, float],
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        document = fitz.open(pdf_path)
        page = document[page_number - 1]
        pixmap = page.get_pixmap(dpi=200, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

        scale_x = pixmap.width / page.rect.width
        scale_y = pixmap.height / page.rect.height

        crop_box = _scale_box(_pad_box(bbox, 16, page.rect.width, page.rect.height), scale_x, scale_y)
        row_box = _scale_box(row_bbox, scale_x, scale_y)
        crop = image.crop(crop_box)

        overlay = Image.new("RGBA", crop.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        relative = (
            row_box[0] - crop_box[0],
            row_box[1] - crop_box[1],
            row_box[2] - crop_box[0],
            row_box[3] - crop_box[1],
        )
        cw, ch = crop.size
        relative = (
            max(0, int(relative[0])),
            max(0, int(relative[1])),
            min(cw, int(relative[2])),
            min(ch, int(relative[3])),
        )
        draw.rectangle(relative, fill=(255, 230, 0, 76), outline=(230, 180, 0, 220), width=3)
        Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB").save(output_path)
        document.close()
        return output_path


def _pad_box(
    box: tuple[float, float, float, float],
    padding: float,
    max_width: float,
    max_height: float,
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = box
    return (
        max(0.0, x0 - padding),
        max(0.0, y0 - padding),
        min(max_width, x1 + padding),
        min(max_height, y1 + padding),
    )


def _scale_box(
    box: tuple[float, float, float, float],
    scale_x: float,
    scale_y: float,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (int(x0 * scale_x), int(y0 * scale_y), int(x1 * scale_x), int(y1 * scale_y))
