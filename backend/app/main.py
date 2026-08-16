"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import init_db
from app.api.routes import admin, auth, documents, chat, conversations, feedback, system
from app.services.admin_bootstrap import ensure_bootstrap_admin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_environment.lower() not in {"development", "test"} and settings.insecure_jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY must be configured outside development/test.")
    init_db()
    ensure_bootstrap_admin()
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


app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
app.include_router(system.router)
app.include_router(admin.router)
