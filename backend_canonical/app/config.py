from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import cache

class _Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8",extra="ignore",)

    APP_NAME = "Ontology Knowledge Graph"
    DEBUG = True

    PG_URL: str = ""
    DB_CONNECT_TIMEOUT_SEC: int = 10
    DB_COMMAND_TIMEOUT_SEC: int = 20
    DB_POOL_TIMEOUT_SEC: int = 10
    DB_STATEMENT_TIMEOUT_MS: int = 20000
    DB_LOCK_TIMEOUT_MS: int = 5000

    NEO4J_URI:str  = "NEO4J_URI"
    NEO4J_USER:str = "NEO4J_USER"
    NEO4J_PASSWORD:str = "NEO4J_PASSWORD"

    # EMBEDDER_API_KEY = os.getenv("EMBEDDER_API_KEY", "ollama")
    # EMBEDDER_MODEL = os.getenv("EMBEDDER_MODEL", "bge-m3:latest")
    # EMBEDDER_DIM = int(os.getenv("EMBEDDER_DIM", "1024"))
    # EMBEDDER_BASE_URL = os.getenv("EMBEDDER_BASE_URL", "http://localhost:11434")

    # GROQ_API_KEY: str = ""
    # GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    # GROQ_MODEL_ID: str = "openai/gpt-oss-120b"
    
    # GUARDRAIL_ENABLE_LLM_JUDGE: bool = True
    # PII_MINIMIZE_RAG_EVIDENCE: bool = True

@cache
def get_settings_singleton()-> _Settings:
    return _Settings()













