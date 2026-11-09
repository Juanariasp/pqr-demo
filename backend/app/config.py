from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_mode: Literal["local", "cloud"] = "local"
    ai_mode: Literal["rules", "gemini"] = "rules"
    google_cloud_project: str = "demo-pqr-local"
    firebase_project_id: str = ""
    firebase_web_api_key: str = ""
    storage_bucket: str = ""
    google_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    data_dir: Path = Path(".data")
    max_upload_mb: int = 5
    max_text_chars: int = 20000
    analysis_timeout_seconds: int = 90

    def validate_runtime(self):
        import os

        if os.getenv("K_SERVICE") and self.app_mode != "cloud":
            raise RuntimeError(
                "Cloud Run requiere APP_MODE=cloud. El acceso local está deshabilitado."
            )
        if self.app_mode == "cloud":
            if not self.firebase_web_api_key or not self.storage_bucket:
                raise RuntimeError("Configura FIREBASE_WEB_API_KEY y STORAGE_BUCKET.")
            if os.getenv("FIREBASE_AUTH_EMULATOR_HOST"):
                raise RuntimeError("No se permiten tokens de emulador en cloud.")
        if self.ai_mode == "gemini" and not self.google_api_key:
            raise RuntimeError("Configura GOOGLE_API_KEY para Google ADK y Gemini.")


@lru_cache
def settings():
    return Settings()
