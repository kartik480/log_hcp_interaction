from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "mysql+pymysql://crm_user:crm_pass@127.0.0.1:3306/hcp_crm"
    openrouter_api_key: str = ""
    openrouter_model_primary: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    openrouter_model_fallback: str = "meta-llama/llama-3.3-70b-instruct:free"
    api_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"


settings = Settings()
