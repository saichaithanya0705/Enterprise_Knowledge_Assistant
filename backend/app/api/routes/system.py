"""Health check and system status (which backends are actually live)."""
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/api/system", tags=["system"])
settings = get_settings()


@router.get("/status")
def status():
    return {
        "status": "ok",
        "key_gateway_configured": settings.key_gateway_configured,
        "nvidia_configured": settings.nvidia_configured,
        "chat_model": settings.key_gateway_chat_model if settings.key_gateway_configured else "local_fallback (extractive)",
        "embedding_model": settings.nvidia_embedding_model if settings.nvidia_configured else "local_fallback (hashing)",
        "rerank_model": settings.nvidia_rerank_model if settings.nvidia_configured else "local_fallback (lexical overlap)",
        "vector_store": "chromadb",
    }
