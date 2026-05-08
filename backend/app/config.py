from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "app.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    db_path: str = str(DEFAULT_DB_PATH)

    evolution_url: str = "http://localhost:8080"
    evolution_api_key: str = "whatsapp_sender_secret_key_2024"
    instance_name: str = "business_sender"

    alert_phone: str = "5561993226767"
    frontend_url: str = "http://localhost:5173"
    # URL que o Evolution usa pra chamar nosso webhook (dentro da rede Docker).
    # Quando rodando via docker-compose, o serviço backend é acessível como http://backend:8000.
    webhook_base_url: str = "http://backend:8000"

    bot_window_start: int = 8
    bot_window_end: int = 18

    worker_tick_seconds: int = 60
    default_send_delay_seconds: int = 60

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.db_path}"


settings = Settings()
