import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import MAX_UPLOAD_BYTES
from app.schemas import Citation, DocumentSummary, QueryRequest, QueryResponse
from app.services.database import connection
from app.services.ingestion import ingest_document
from app.services.llm import ExtractiveProvider, get_provider
from app.services.retrieval import retrieve


router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/documents", response_model=list[DocumentSummary])
def list_documents() -> list[dict]:
    with connection() as db:
        rows = db.execute(
            """SELECT documents.id, filename, file_type, page_count, created_at,
                      COUNT(chunks.id) AS chunk_count
               FROM documents LEFT JOIN chunks ON chunks.document_id = documents.id
               GROUP BY documents.id ORDER BY created_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


@router.post("/documents/upload")
async def upload_documents(files: list[UploadFile] = File(...)) -> dict:
    results = []
    for file in files:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{file.filename} exceeds the 25 MB upload limit.")
        try:
            results.append(ingest_document(file.filename or "upload.txt", content))
        except ValueError as error:
            raise HTTPException(status_code=400, detail=f"{file.filename}: {error}") from error
    return {"documents": results}


@router.delete("/documents/{document_id}")
def delete_document(document_id: str) -> dict[str, str]:
    with connection() as db:
        db.execute("PRAGMA foreign_keys = ON")
        cursor = db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "deleted"}


@router.post("/query", response_model=QueryResponse)
def query_documents(request: QueryRequest) -> QueryResponse:
    passages = retrieve(request.question, request.top_k)
    try:
        provider = get_provider()
        answer = provider.answer(request.question, passages)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        logger.warning("LLM provider failed with %s; returning retrieved excerpts.", type(error).__name__)
        provider = ExtractiveProvider()
        answer = "The configured LLM failed, so review the retrieved source passages below. " + provider.answer(
            request.question, passages
        )
    return QueryResponse(
        answer=answer,
        citations=[
            Citation(
                document_id=item["document_id"],
                filename=item["filename"],
                page=item["page"],
                excerpt=item["content"],
                score=item["score"],
            )
            for item in passages
        ],
        provider=provider.name,
    )