from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRES_IN: int
    REFRESH_TOKEN_EXPIRES_IN: int

    project_root: Path = Path(__file__).parent.parent.resolve()

    REDIS_URL: str

    YOUTUBE_API_KEY: str

    EMAIL_HOST: str = "smtp.yandex.com"
    EMAIL_PORT: int = 465
    EMAIL_USE_TLS: bool
    EMAIL_PASSWORD: str
    EMAIL_FROM: str
    
    IMAGES_FOLDER: Path = Path("./static/images")
    
    REGISTRATION_TOKEN_PATH: str
    PASS_RESTORE_TOKEN_PATH: str
    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
