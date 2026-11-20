from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    indodax_api_key: str
    indodax_secret_key: str
    indodax_base_url: str = "https://api.indodax.com"
    indodax_recv_window: int = 5000
    indodax_enable_live_withdrawal: bool = False
    indodax_withdraw_allowlist: str = "[]"
    indodax_idr_withdraw_allowlist: str = "[]"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()