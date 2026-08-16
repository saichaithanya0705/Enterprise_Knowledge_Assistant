"""Application configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Key Gateway - used for chat/answer generation only. Never hardcode,
    # never sent to the frontend.
    key_gateway_url: str = ""
    key_gateway_api_key: str = ""
    key_gateway_chat_model: str = "gpt-4o-mini"

    # NVIDIA NIM API - used for embeddings + reranking only. Never hardcode,
    # never sent to the frontend.
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    # NOTE: NVIDIA retired the old ai.api.nvidia.com/v1/retrieval/.../reranking
    # endpoint (returns 404 now). Reranking is served from the same host as
    # embeddings/chat under /v1/ranking.
    nvidia_rerank_url: str = "https://integrate.api.nvidia.com/v1/ranking"
    nvidia_embedding_model: str = "nvidia/nv-embedqa-e5-v5"
    nvidia_rerank_model: str = "nvidia/nv-rerankqa-mistral-4b-v3"
    nvidia_chat_model: str = "meta/llama-3.1-8b-instruct"

    # Authentication. Production deployments must override the development
    # secret; startup rejects the placeholder outside local/test databases.
    jwt_secret_key: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    database_url: str = "sqlite:///./data/knowledge_assistant.db"
    app_environment: str = "development"
    chroma_persist_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    chunk_size: int = 800
    chunk_overlap: int = 120
    top_k_retrieval: int = 8
    top_k_final_context: int = 4
    similarity_threshold: float = 0.15

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def key_gateway_configured(self) -> bool:
        return bool(self.key_gateway_url and self.key_gateway_api_key)

    @property
    def nvidia_configured(self) -> bool:
        return bool(self.nvidia_api_key)

    @property
    def insecure_jwt_secret(self) -> bool:
        return self.jwt_secret_key in {"", "dev-only-change-me", "change-me"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
