from __future__ import annotations

import os
from pathlib import Path


def extract_text_from_pdf(path: str | Path) -> str:
    pdf_path = Path(path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        return ""

    reader_cls = _import_pdf_reader()
    if reader_cls is None:
        return ""

    try:
        reader = reader_cls(str(pdf_path))
    except Exception:
        return ""

    parts: list[str] = []
    for page in getattr(reader, "pages", []):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        if page_text.strip():
            parts.append(page_text.strip())

    extracted_text = "\n".join(parts).strip()
    if extracted_text:
        return extracted_text

    return _extract_text_with_ocr(pdf_path)


def _import_pdf_reader() -> object | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None

    return PdfReader


def _extract_text_with_ocr(pdf_path: Path) -> str:
    fitz_module = _import_fitz()
    image_cls = _import_pillow_image()
    pytesseract_module = _import_pytesseract()
    if fitz_module is None or image_cls is None or pytesseract_module is None:
        return ""

    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if tesseract_cmd:
        pytesseract_module.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        document = fitz_module.open(pdf_path)
    except Exception:
        return ""

    parts: list[str] = []
    try:
        for page_index in range(min(document.page_count, 5)):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz_module.Matrix(2, 2), alpha=False)
            image = image_cls.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )
            try:
                page_text = pytesseract_module.image_to_string(image, lang="ces+eng")
            except Exception:
                page_text = ""
            if page_text.strip():
                parts.append(page_text.strip())
    finally:
        document.close()

    return "\n".join(parts).strip()


def _import_fitz() -> object | None:
    try:
        import fitz
    except ImportError:
        return None

    return fitz


def _import_pillow_image() -> object | None:
    try:
        from PIL import Image
    except ImportError:
        return None

    return Image


def _import_pytesseract() -> object | None:
    try:
        import pytesseract
    except ImportError:
        return None

    return pytesseract
