from pathlib import Path

import pytest
from pydantic import ValidationError

from src.config import PROJECT_ROOT, _resolve_env_path, get_config
from src.models.config import Config


class TestResolveEnvPath:
    def test_none_returns_default(self):
        result = _resolve_env_path(None)
        assert result == PROJECT_ROOT / ".env"

    def test_relative_resolves_to_project_root(self):
        result = _resolve_env_path("custom.env")
        assert result == PROJECT_ROOT / "custom.env"

    def test_absolute_returns_unchanged(self):
        result = _resolve_env_path("/abs/path/.env")
        assert result == Path("/abs/path/.env")


class TestGetConfig:
    def test_loads_example_env_file(self):
        """Файл .env.example должен загружаться и проходить валидацию."""
        get_config(".env.example")

    def test_extra_env_vars_ignored(self, monkeypatch: pytest.MonkeyPatch):
        """Лишние переменные окружения должны игнорироваться."""
        monkeypatch.setenv("EXTRA_UNKNOWN_PARAM", "should-be-ignored")

        config = get_config(".env.example")

        assert not hasattr(config, "EXTRA_UNKNOWN_PARAM")

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError, match="Файл конфигурации не найден"):
            get_config("/nonexistent/path/.env")

    def test_invalid_port_zero_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("BACKEND_PORT", "0")

        with pytest.raises(ValidationError):
            get_config(".env.example")

    def test_empty_host_raises(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("BACKEND_HOST", "")

        with pytest.raises(ValidationError):
            get_config(".env.example")


class TestConfigComputedProperties:
    def test_db_app_url(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DB_APP_USERNAME", "user")
        monkeypatch.setenv("DB_APP_PASSWORD", "secret")
        monkeypatch.setenv("DB_HOST", "db")
        monkeypatch.setenv("DB_PORT", "5432")
        monkeypatch.setenv("DB_APP_DATABASE", "app_db")

        config = get_config(".env.example")

        assert config.db_app_url == (
            "postgresql://user:secret@db:5432/app_db"
        )

    def test_db_app_sa_url(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DB_APP_USERNAME", "user")
        monkeypatch.setenv("DB_APP_PASSWORD", "secret")
        monkeypatch.setenv("DB_HOST", "db")
        monkeypatch.setenv("DB_PORT", "5432")
        monkeypatch.setenv("DB_APP_DATABASE", "app_db")

        config = get_config(".env.example")

        assert config.db_app_sa_url == (
            "postgresql+psycopg://user:secret@db:5432/app_db"
        )

    def test_db_default_url(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("DB_DEFAULT_USERNAME", "admin")
        monkeypatch.setenv("DB_DEFAULT_PASSWORD", "admin_secret")
        monkeypatch.setenv("DB_HOST", "db")
        monkeypatch.setenv("DB_PORT", "15432")
        monkeypatch.setenv("DB_DEFAULT_DATABASE", "postgres")

        config = get_config(".env.example")

        assert config.db_default_url == (
            "postgresql://admin:admin_secret@db:15432/postgres"
        )


class TestConfigFixture:
    """Проверка фикстуры test_config из conftest.py."""

    def test_uses_test_db_name(self, test_config: Config):
        assert "_test_" in test_config.db_app_database
        assert test_config.db_app_database != "app"

    def test_computed_url_includes_test_db(self, test_config: Config):
        assert f"/{test_config.db_app_database}" in test_config.db_app_url

    def test_can_reconstruct_from_dict(self, test_config: Config):
        data = test_config.model_dump()
        data["db_app_database"] = "modified_db"

        cfg = Config(**data)

        assert cfg.db_app_database == "modified_db"
        assert cfg.backend_host == test_config.backend_host
        assert "modified_db" in cfg.db_app_url
