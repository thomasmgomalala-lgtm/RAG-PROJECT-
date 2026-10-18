# Tesla Filing RAG

A local document Q&A app with a React frontend and FastAPI backend. The Tesla 2024 and 2025 Form 10-K filings are bundled as official SEC HTML source documents and indexed automatically at backend startup. You can also upload PDF, TXT, or HTML documents, retrieve relevant passages, and inspect source citations.

## Requirements

- Python 3.10+
- Node.js 20+

## Run the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API documentation is at <http://localhost:8000/docs>.

## Run the frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally <http://localhost:5173>). The frontend proxies `/api` requests to FastAPI.

## How it works

- The bundled Tesla reports are parsed from SEC HTML page breaks and indexed automatically. PDF pages are extracted with `pypdf`; TXT files are also supported.
- Text is split into overlapping chunks and persisted with document metadata in `backend/data/rag.sqlite3`.
- Queries use local TF-IDF-style lexical retrieval. The configured provider is prompted to ground answers in retrieved excerpts and citations; if the provider fails, the API returns a retrieval-only response with the matching passages.
- OpenAI is supported through the official SDK. In `backend/.env`, set `LLM_PROVIDER=openai`, add your OpenAI API key to `LLM_API_KEY`, and choose a model in `LLM_MODEL` (the starter value is `gpt-4.1-mini`). Leave `LLM_BASE_URL` blank to use OpenAI's default endpoint. The `LLMProvider` interface in `backend/app/services/llm.py` remains the extension point for other providers. Answers are prompted to stay grounded in retrieved context; citations are returned separately by the API.

Uploaded files and the SQLite database stay local. Bundled sources are Tesla's SEC filings: 2025 accession `0001628280-26-003952` and 2024 accession `0001628280-25-003063`. They are HTML filings rather than PDFs; page-break metadata is retained for citations.

## Example questions

1. What were Tesla's total revenues in 2025 and 2024?
2. How many consumer vehicles did Tesla deliver in 2025?
3. How many GWh of energy storage products did Tesla deploy in 2025?
4. What were Tesla's automotive and energy storage revenues in 2025?
5. What was Tesla's total gross margin in 2025 compared with 2024?
6. How much cash and short-term investments did Tesla report at year-end 2025?
7. What were Tesla's operating cash flow and capital expenditures in 2025?
8. What risks did Tesla identify around suppliers and battery-cell availability?
9. How many employees did Tesla report at the end of 2025?
10. What related-party revenue and costs did Tesla report for xAI in 2025?

## API

- `GET /api/health`
- `GET /api/documents`
- `POST /api/documents/upload` (multipart `files`)
- `DELETE /api/documents/{document_id}`
- `POST /api/query` with `{ "question": "...", "top_k": 5 }`