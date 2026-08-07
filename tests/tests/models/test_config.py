import pytest
from pydantic import ValidationError

from src.models.config import Config


class TestConfigModel:
    def test_roundtrips_from_test_config(self, test_config: Config):
        data = test_config.model_dump()
        cfg = Config(**data)
        assert cfg.backend_host == test_config.backend_host
        assert cfg.backend_port == test_config.backend_port

    def test_es_url_property(self, test_config: Config):
        assert test_config.es_url == f"http://{test_config.es_host}:{test_config.es_port}"

    def test_port_at_upper_boundary(self, test_config: Config):
        data = test_config.model_dump()
        Config(**{**data, "backend_port": 65535})
        Config(**{**data, "db_port": 65535})
        Config(**{**data, "es_port": 65535})
        Config(**{**data, "ollama_port": 65535})

    def test_port_above_upper_boundary_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "backend_port": 65536})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_port": 65536})
        with pytest.raises(ValidationError):
            Config(**{**data, "es_port": 65536})

    def test_port_zero_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "backend_port": 0})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_port": 0})
        with pytest.raises(ValidationError):
            Config(**{**data, "es_port": 0})

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
        with pytest.raises(ValidationError):
            Config(**{**data, "ollama_host": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "ollama_model": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "ollama_keep_alive": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "ollama_tokenizer": ""})

    def test_empty_es_string_field_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "es_host": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "es_documents_index_name": ""})

    def test_empty_es_superuser_password_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "es_superuser_password": ""})

    def test_empty_password_raises(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "db_default_password": ""})
        with pytest.raises(ValidationError):
            Config(**{**data, "db_app_password": ""})

    def test_es_indices(self, test_config: Config):
        """es_indices содержит все поля es_*_index_name."""
        indices = test_config.es_indices
        assert len(indices) == 4
        assert "es_documents_index_name" in indices
        assert indices["es_documents_index_name"] == test_config.es_documents_index_name
        assert "es_blogposts_index_name" in indices
        assert indices["es_blogposts_index_name"] == test_config.es_blogposts_index_name
        assert "es_blogposts_text_chunks_index_name" in indices
        assert indices["es_blogposts_text_chunks_index_name"] == test_config.es_blogposts_text_chunks_index_name
        assert "es_sales_index_name" in indices
        assert indices["es_sales_index_name"] == test_config.es_sales_index_name

    def test_ollama_url_property(self, test_config: Config):
        assert test_config.ollama_url == f"http://{test_config.ollama_host}:{test_config.ollama_port}"

    def test_ollama_timeout_must_be_positive(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "ollama_timeout": 0})

    def test_ollama_batch_size_must_be_positive(self, test_config: Config):
        data = test_config.model_dump()
        with pytest.raises(ValidationError):
            Config(**{**data, "ollama_batch_size": 0})
