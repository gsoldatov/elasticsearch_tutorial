import pytest
from pydantic import ValidationError

from src.models.config import Config


class TestConfigModel:
    def test_roundtrips_from_test_config(self, test_config: Config):
        data = test_config.model_dump()
        cfg = Config(**data)
        assert cfg.backend_host == test_config.backend_host
        assert cfg.backend_port == test_config.backend_port

    def test_port_at_upper_boundary(self, test_config: Config):
        data = test_config.model_dump()
        Config(**{**data, "backend_port": 65535})
        Config(**{**data, "db_port": 65535})

    def test_port_above_upper_boundary_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "backend_port": 65536})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_port": 65536})

    def test_port_zero_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "backend_port": 0})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_port": 0})

    def test_port_negative_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "backend_port": -1})

    def test_empty_string_field_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "backend_host": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_host": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_app_database": ""})

    def test_password_can_be_empty(self, test_config: Config):
        data = test_config.model_dump()
        cfg = Config(**{**data, "db_default_password": "", "db_app_password": ""})
        assert cfg.db_default_password == ""
        assert cfg.db_app_password == ""
