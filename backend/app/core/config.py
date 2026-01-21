from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "CMAC Bot Correos"
    EXCHANGE_SERVER: str = "webmail.cajaarequipa.pe"
    SESSION_TIME_LIMIT: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8')

settings = Settings()
