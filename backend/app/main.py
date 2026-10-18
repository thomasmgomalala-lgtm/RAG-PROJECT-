from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.api import router
from app.services.database import initialize_database
from app.services.ingestion import seed_bundled_documents


app = FastAPI(title="Tesla Filing RAG API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.on_event("startup")
def startup() -> None:
    initialize_database()
    seed_bundled_documents()