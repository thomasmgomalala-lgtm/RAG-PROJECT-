from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    id: str
    filename: str
    file_type: str
    page_count: int | None
    chunk_count: int
    created_at: str


class QueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class Citation(BaseModel):
    document_id: str
    filename: str
    page: int | None
    excerpt: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    provider: str