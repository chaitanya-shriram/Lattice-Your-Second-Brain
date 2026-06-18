from pathlib import Path
from typing import Optional
from utils.logger import get_logger

log = get_logger("utils.file_utils")

SUPPORTED_EXTENSIONS = {".pdf", ".epub", ".md", ".txt", ".docx"}


def extract_text(file_path: Path, max_chars: int = 8000) -> str:
    """Extract text from a file. Returns first max_chars characters."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return _extract_pdf(file_path, max_chars)
    elif ext == ".epub":
        return _extract_epub(file_path, max_chars)
    elif ext == ".docx":
        return _extract_docx(file_path, max_chars)
    elif ext in {".md", ".txt"}:
        return _extract_text_file(file_path, max_chars)
    else:
        log.warning(f"Unsupported file type: {ext}")
        return ""


def _extract_pdf(path: Path, max_chars: int) -> str:
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages[:4]:  # first 4 pages
                text += (page.extract_text() or "") + "\n"
                if len(text) >= max_chars:
                    break
        return text[:max_chars]
    except ImportError:
        log.warning("pdfplumber not installed. pip install pdfplumber")
        return f"[PDF: {path.name}]"
    except Exception as e:
        log.error(f"PDF extraction failed for {path}: {e}")
        return f"[PDF extraction error: {path.name}]"


def _extract_epub(path: Path, max_chars: int) -> str:
    try:
        import ebooklib
        from ebooklib import epub
        from html.parser import HTMLParser

        class _HTMLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
            def handle_data(self, data):
                self.text.append(data)
            def get_text(self):
                return " ".join(self.text)

        book = epub.read_epub(str(path))
        text = ""
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            stripper = _HTMLStripper()
            stripper.feed(item.content.decode("utf-8", errors="ignore"))
            text += stripper.get_text() + "\n"
            if len(text) >= max_chars:
                break
        return text[:max_chars]
    except ImportError:
        log.warning("ebooklib not installed. pip install ebooklib")
        return f"[EPUB: {path.name}]"
    except Exception as e:
        log.error(f"EPUB extraction failed for {path}: {e}")
        return f"[EPUB extraction error: {path.name}]"


def _extract_docx(path: Path, max_chars: int) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        text = "\n".join(p.text for p in doc.paragraphs)
        return text[:max_chars]
    except ImportError:
        log.warning("python-docx not installed. pip install python-docx")
        return f"[DOCX: {path.name}]"
    except Exception as e:
        log.error(f"DOCX extraction failed for {path}: {e}")
        return f"[DOCX extraction error: {path.name}]"


def _extract_text_file(path: Path, max_chars: int) -> str:
    try:
        try:
            import chardet
            raw = path.read_bytes()
            detected = chardet.detect(raw)
            encoding = detected.get("encoding") or "utf-8"
        except ImportError:
            encoding = "utf-8"
        return path.read_text(encoding=encoding, errors="replace")[:max_chars]
    except Exception as e:
        log.error(f"Text extraction failed for {path}: {e}")
        return f"[Text extraction error: {path.name}]"


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS
