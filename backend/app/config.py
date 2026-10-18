import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data"))
SEED_DATA_DIR = Path(__file__).resolve().parent / "seed_data"
DATABASE_PATH = DATA_DIR / "rag.sqlite3"
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".html"}