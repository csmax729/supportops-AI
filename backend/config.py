from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    data_dir: Path = Path("runtime")
    admin_key: SecretStr = SecretStr("")
    provider: Literal["ollama", "openai", "llamacpp"] = "ollama"
    llama_url: str = "http://127.0.0.1:8080"
    chat_model: str = "qwen2.5:3b"
    ollama_url: str = "http://localhost:11434"
    openai_api_key: SecretStr = SecretStr("")
    temperature: float = Field(0, ge=0, le=1)
    provider_timeout: int = Field(90, ge=1, le=300)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_revision: str = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
    chunk_words: int = Field(130, ge=20, le=600)
    overlap_words: int = Field(24, ge=0, le=100)
