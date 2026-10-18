import hashlib
import io
import re
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser

from pypdf import PdfReader

from app.config import ALLOWED_EXTENSIONS, SEED_DATA_DIR
from app.services.database import connection


class FilingHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.pages: list[list[str]] = [[]]
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.skip_depth += 1
        elif tag == "hr" and any(
            name == "style" and value and "page-break-after" in value
            for name, value in attrs
        ):
            if any(part.strip() for part in self.pages[-1]):
                self.pages.append([])
        elif tag in {"br", "div", "p", "tr", "li", "h1", "h2", "h3"}:
            self.pages[-1].append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        elif tag in {"div", "p", "tr", "li", "h1", "h2", "h3"}:
            self.pages[-1].append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.pages[-1].append(data)


def extract_html_pages(content: bytes) -> list[tuple[int, str]]:
    parser = FilingHTMLParser()
    parser.feed(content.decode("utf-8", errors="replace"))
    return [
        (index + 1, re.sub(r"\s+", " ", " ".join(parts)).strip())
        for index, parts in enumerate(parser.pages)
        if any(part.strip() for part in parts)
    ]


def split_text(text: str, chunk_size: int = 220, overlap: int = 40) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start = end - overlap
    return chunks


def extract_pages(filename: str, content: bytes) -> tuple[list[tuple[int | None, str]], int | None]:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if f".{extension}" not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF and TXT files are supported.")

    if extension == "pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = [(index + 1, page.extract_text() or "") for index, page in enumerate(reader.pages)]
        if not any(text.strip() for _, text in pages):
            raise ValueError("No selectable text found in this PDF. Scanned PDFs need OCR before upload.")
        return pages, len(reader.pages)

    if extension == "html":
        pages = extract_html_pages(content)
        if not pages:
            raise ValueError("This HTML file contains no readable text.")
        return pages, max(page for page, _ in pages)

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("TXT files must use UTF-8 encoding.") from error
    if not text.strip():
        raise ValueError("This file contains no text.")
    return [(None, text)], None


def ingest_document(filename: str, content: bytes) -> dict:
    content_hash = hashlib.sha256(content).hexdigest()
    with connection() as db:
        existing = db.execute("SELECT id, filename FROM documents WHERE content_hash = ?", (content_hash,)).fetchone()
        if existing:
            return {"id": existing["id"], "filename": existing["filename"], "duplicate": True, "chunk_count": 0}

    pages, page_count = extract_pages(filename, content)
    document_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    chunks = []
    for page, text in pages:
        chunks.extend((page, chunk) for chunk in split_text(text))

    with connection() as db:
        db.execute(
            "INSERT INTO documents (id, filename, file_type, content_hash, page_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, filename, filename.rsplit(".", 1)[-1].lower(), content_hash, page_count, created_at),
        )
        db.executemany(
            "INSERT INTO chunks (document_id, chunk_index, page, content) VALUES (?, ?, ?, ?)",
            [(document_id, index, page, text) for index, (page, text) in enumerate(chunks)],
        )

    return {"id": document_id, "filename": filename, "duplicate": False, "chunk_count": len(chunks), "page_count": page_count}


def seed_bundled_documents() -> list[dict]:
    return [
        ingest_document(path.name, path.read_bytes())
        for path in sorted(SEED_DATA_DIR.glob("*.html"))
    ]