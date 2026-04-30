import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PG_URL: str = os.environ.get("BIGWELD_V2_PG_URL", "postgresql:///aegis")
    NAS_VLLM_URL: str = os.environ.get(
        "BIGWELD_V2_NAS_VLLM_URL",
        "http://192.168.0.25:8005/v1",
    )
    DEEPINFRA_API_KEY: str = os.environ.get("DEEPINFRA_API_KEY", "")
    DEEPINFRA_BASE_URL: str = "https://api.deepinfra.com/v1/openai"
    MODEL_NAME: str = "Qwen/Qwen3.6-35B-A3B"
    MCP_URL: str = "http://192.168.0.30:8885/mcp/"
    EMBEDDING_URL: str = os.environ.get(
        "BIGWELD_V2_EMBEDDING_URL",
        "http://192.168.0.25:8002/v1",
    )


settings = Settings()
