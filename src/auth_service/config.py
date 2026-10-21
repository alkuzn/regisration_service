from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Base(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )


class BaseConnectionSettings(Base):
    host: str
    port: int
    user: str
    password: str


class DBSettings(BaseConnectionSettings):
    dbname: str
    model_config = SettingsConfigDict(env_prefix="DB_")

    def __db_url_(self, driver):
        return f"{driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

    @property
    def asyncurl(self) -> str:
        return self._DBSettings__db_url_(  # ty: ignore[unresolved-attribute]
            "postgresql+asyncpg"
        )

    @property
    def syncurl(self) -> str:
        return self._DBSettings__db_url_(  # ty: ignore[unresolved-attribute]
            "postgresql+psycopg"
        )


class RedisSettings(BaseConnectionSettings):
    model_config = SettingsConfigDict(env_prefix="REDIS_")

    @property
    def url(self) -> str:
        return f"redis://{self.user}:{self.password}@{self.host}:{self.port}"


class FastAPISettings(Base):
    docs_url: str | None = Field(default=None)
    redoc_url: str | None = Field(default=None)
    openapi_url: str | None = Field(default=None)
    model_config = SettingsConfigDict(env_prefix="FASTAPI_")


class UvicornSettings(Base):
    app: str
    reload: bool = Field(default=False)
    model_config = SettingsConfigDict(env_prefix="UVICORN_")


class AppSettings(Base):
    host: str
    port: int
    key_path: str
    model_config = SettingsConfigDict(env_prefix="APP_")


class Settings(Base):
    redis: RedisSettings = RedisSettings()
    db: DBSettings = DBSettings()
    fastapi: FastAPISettings = FastAPISettings()
    uvicorn: UvicornSettings = UvicornSettings()
    app: AppSettings = AppSettings()


settings = Settings()
