"""Runtime configuration.

Single source of truth — every module that needs an env-derived value
imports `settings` from here rather than reading `os.environ` directly.
That way the failure mode for a missing env var is a clear Pydantic
validation error at startup instead of a KeyError deep in a request
handler.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="GRADLENS_",
        extra="ignore",
    )

    # Service identity
    env: str = "dev"  # "dev" | "prod"
    log_level: str = "INFO"

    # Data root — LanceDB index + SQLite metadata live under here.
    # Kept out of git via the root .gitignore (data/).
    data_dir: Path = Path("data")

    # CORS — which origins the Next.js web app is allowed to call from.
    # In prod this will be the deployed Vercel URL; in dev we accept
    # localhost so `pnpm dev` and `uv run uvicorn` can talk to each
    # other without extra config.
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


settings = Settings()
