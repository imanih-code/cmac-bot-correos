from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "CMAC Bot Correos"
    EXCHANGE_SERVER: str = "webmail.cajaarequipa.pe"

    class Config:
        env_file = ".env"

settings = Settings()
