from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Social Debt API Model"
    API_V1_STR: str = "/api/v1"
    API_SECRET_KEY: str = "super_secret_social_debt_key_2024"
    
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
