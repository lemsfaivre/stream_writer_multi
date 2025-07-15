from pathlib import Path

from settings import AppSettings


def test_settings_load():
    settings = AppSettings.from_toml(Path("settings.toml"))
    assert settings.globals.queue_maxsize > 0
