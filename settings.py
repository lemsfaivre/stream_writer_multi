import sys
import tomllib
from pathlib import Path
from typing import Annotated, Any

from loguru import logger as base_logger
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import BaseModel, Field, HttpUrl, PositiveInt, ValidationError


class GlobalSettings(BaseModel):
    queue_maxsize: PositiveInt = 1000
    max_retries: Annotated[int, Field(default=5, ge=0, le=20)]
    max_duration_secs: Annotated[int, Field(default=15, ge=10, le=28800)]


class SourceSettings(BaseModel):
    url: HttpUrl
    output_stream: PositiveInt


class OutputSettings(BaseModel):
    stream: PositiveInt
    filename: str


class AppSettings(BaseSettings):
    globals: GlobalSettings
    sources: dict[str, SourceSettings]
    outputs: dict[str, OutputSettings]

    model_config: SettingsConfigDict = SettingsConfigDict(env_file=None, env_prefix="", extra="forbid")

    @classmethod
    def from_toml(cls, path: Path = Path("./settings.toml")) -> "AppSettings":
        data: dict[str, Any] = dict()
        try:
            data = tomllib.load(path.open(mode="rb"))
            settings: "AppSettings" = cls(**data)
        except (FileNotFoundError, tomllib.TOMLDecodeError, ValidationError, Exception) as e:
            raise e

        return settings


try:
    settings_path: Path = Path(__file__).with_suffix(".toml")
    gl_settings: AppSettings = AppSettings.from_toml(path=settings_path)
except Exception as e:
    base_logger.error(f"Cannot read settings file: {settings_path.resolve()}!")
    base_logger.error(f"{repr(e)}")
    sys.exit()
