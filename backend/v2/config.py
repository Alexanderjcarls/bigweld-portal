import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PG_URL: str = os.environ.get("BIGWELD_V2_PG_URL", "postgresql:///aegis")
    MODEL: str = os.environ.get("BIGWELD_V2_MODEL", "claude-sonnet-4-6")
    DEEPINFRA_API_KEY: str = os.environ.get("DEEPINFRA_API_KEY", "")
    # Trailing slash matters: bigweld-mcp serves this path directly.
    MCP_URL: str = os.environ.get("BIGWELD_V2_MCP_URL", "http://192.168.0.30:8885/mcp/")
    EMBEDDING_URL: str = os.environ.get(
        "BIGWELD_V2_EMBEDDING_URL",
        "http://192.168.0.25:8002/v1",
    )


settings = Settings()
