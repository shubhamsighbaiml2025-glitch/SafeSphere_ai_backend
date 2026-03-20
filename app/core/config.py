from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SafeSphere AI Backend"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_workers: int = 2
    api_prefix: str = "/api"
    mongo_uri: str = Field(default="mongodb://localhost:27017")
    mongo_db_name: str = Field(default="safesphere")
    jwt_secret_key: str = Field(default="change-this-secret-in-production")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60 * 24)
    cors_origins: str = ""
    trusted_hosts: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    def _split_csv(self, value: str) -> list[str]:
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return self._split_csv(self.cors_origins)

    @property
    def trusted_hosts_list(self) -> list[str]:
        return self._split_csv(self.trusted_hosts) or ["*"]


settings = Settings()
