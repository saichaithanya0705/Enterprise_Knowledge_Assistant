"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.routes import documents, chat, conversations, feedback, system

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Enterprise Knowledge Assistant API",
    description="RAG-powered internal knowledge base assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"service": "enterprise-knowledge-assistant", "status": "running"}


app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
app.include_router(system.router)
