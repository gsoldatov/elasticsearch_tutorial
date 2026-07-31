from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models.blogpost import Blogpost, BlogpostCreate, BlogpostUpdate


def _valid_create_data() -> dict:
    return {
        "title": "Заголовок",
        "text": "Текст блогпоста",
        "tags": ["python", "elastic"],
    }


def _valid_blogpost_data() -> dict:
    return {
        "id": "abc123",
        "title": "Заголовок",
        "text": "Текст блогпоста",
        "tags": ["python", "elastic"],
        "updated_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }


# ── BlogpostCreate ─────────────────────────────────────────────────────────


class TestBlogpostCreate:
    # Ошибки валидации

    def test_title_empty_raises(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "title": ""})

    def test_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "title": "x" * 257})

    def test_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "text": "x" * 8193})

    def test_tags_too_many_raises(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "tags": ["t"] * 101})

    def test_tag_empty_raises(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "tags": [""]})

    def test_tag_too_long_raises(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "tags": ["x" * 65]})

    def test_strict_mode_rejects_coercion(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "title": 123})

    # Бизнес-логика

    def test_empty_text_allowed(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "text": ""})
        assert bp.text == ""

    def test_empty_tags_allowed(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "tags": []})
        assert bp.tags == []

    # Граничные случаи

    def test_title_exact_max_length(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "title": "x" * 256})
        assert len(bp.title) == 256

    def test_text_exact_max_length(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "text": "x" * 8192})
        assert len(bp.text) == 8192

    def test_tags_exact_max_count(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "tags": ["t"] * 100})
        assert len(bp.tags) == 100

    def test_tag_exact_min_length(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "tags": ["x"]})
        assert bp.tags == ["x"]

    def test_tag_exact_max_length(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "tags": ["x" * 64]})
        assert len(bp.tags[0]) == 64

    # Happy path

    def test_roundtrip(self):
        data = _valid_create_data()
        bp = BlogpostCreate(**data)
        assert bp.title == data["title"]
        assert bp.text == data["text"]
        assert bp.tags == data["tags"]

    def test_defaults_id_and_updated_at_none(self):
        bp = BlogpostCreate(**_valid_create_data())
        assert bp.id is None
        assert bp.updated_at is None

    def test_with_optional_id(self):
        bp = BlogpostCreate(**{**_valid_create_data(), "id": "my-custom-id"})
        assert bp.id == "my-custom-id"

    def test_with_optional_updated_at(self):
        now = datetime.now(timezone.utc)
        bp = BlogpostCreate(**{**_valid_create_data(), "updated_at": now})
        assert bp.updated_at == now

    def test_with_both_optionals(self):
        now = datetime.now(timezone.utc)
        bp = BlogpostCreate(
            **_valid_create_data(), id="abc", updated_at=now,
        )
        assert bp.id == "abc"
        assert bp.updated_at == now

    def test_strict_id_rejects_int(self):
        with pytest.raises(ValidationError):
            BlogpostCreate(**{**_valid_create_data(), "id": 123})


# ── BlogpostUpdate ─────────────────────────────────────────────────────────


class TestBlogpostUpdate:
    # Ошибки валидации

    def test_all_fields_none_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            BlogpostUpdate()
        assert "At least one non-null field" in str(exc_info.value)

    def test_all_fields_explicit_none_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            BlogpostUpdate(title=None, text=None, tags=None, updated_at=None)
        assert "At least one non-null field" in str(exc_info.value)

    def test_title_empty_raises(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(title="")

    def test_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(title="x" * 257)

    def test_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(text="x" * 8193)

    def test_tags_too_many_raises(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(tags=["t"] * 101)

    def test_tag_empty_raises(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(tags=[""])

    def test_tag_too_long_raises(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(tags=["x" * 65])

    def test_strict_mode_rejects_coercion(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(title=123)

    # Граничные случаи

    def test_single_field_valid(self):
        bp = BlogpostUpdate(title="Новый заголовок")
        assert bp.title == "Новый заголовок"

    def test_empty_text_allowed(self):
        bp = BlogpostUpdate(text="")
        assert bp.text == ""

    def test_empty_tags_allowed(self):
        bp = BlogpostUpdate(tags=[])
        assert bp.tags == []

    def test_title_exact_max_length(self):
        bp = BlogpostUpdate(title="x" * 256)
        assert len(bp.title) == 256

    def test_tags_exact_max_count(self):
        bp = BlogpostUpdate(tags=["t"] * 100)
        assert len(bp.tags) == 100

    def test_tag_exact_min_length(self):
        bp = BlogpostUpdate(tags=["x"])
        assert bp.tags == ["x"]

    def test_tag_exact_max_length(self):
        bp = BlogpostUpdate(tags=["x" * 64])
        assert len(bp.tags[0]) == 64

    # Happy path

    def test_all_fields_set(self):
        bp = BlogpostUpdate(title="T", text="X", tags=["a"])
        assert bp.title == "T"
        assert bp.text == "X"
        assert bp.tags == ["a"]

    def test_only_updated_at_valid(self):
        now = datetime.now(timezone.utc)
        bp = BlogpostUpdate(updated_at=now)
        assert bp.updated_at == now

    def test_updated_at_with_title(self):
        now = datetime.now(timezone.utc)
        bp = BlogpostUpdate(updated_at=now, title="T")
        assert bp.updated_at == now
        assert bp.title == "T"

    def test_strict_updated_at_rejects_non_datetime(self):
        with pytest.raises(ValidationError):
            BlogpostUpdate(updated_at=123)


# ── Blogpost ───────────────────────────────────────────────────────────────


class TestBlogpost:
    # Ошибки валидации

    def test_strict_mode_rejects_int_for_id(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "id": 123})

    def test_title_empty_raises(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "title": ""})

    def test_title_too_long_raises(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "title": "x" * 257})

    def test_text_too_long_raises(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "text": "x" * 8193})

    def test_tags_too_many_raises(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "tags": ["t"] * 101})

    def test_tag_empty_raises(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "tags": [""]})

    def test_tag_too_long_raises(self):
        with pytest.raises(ValidationError):
            Blogpost(**{**_valid_blogpost_data(), "tags": ["x" * 65]})

    # Граничные случаи

    def test_id_any_string(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "id": "z9x8c7v6b5n4m3"})
        assert bp.id == "z9x8c7v6b5n4m3"

    def test_empty_text_allowed(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "text": ""})
        assert bp.text == ""

    def test_empty_tags_allowed(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "tags": []})
        assert bp.tags == []

    def test_title_exact_max_length(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "title": "x" * 256})
        assert len(bp.title) == 256

    def test_text_exact_max_length(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "text": "x" * 8192})
        assert len(bp.text) == 8192

    def test_tags_exact_max_count(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "tags": ["t"] * 100})
        assert len(bp.tags) == 100

    def test_tag_exact_min_length(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "tags": ["x"]})
        assert bp.tags == ["x"]

    def test_tag_exact_max_length(self):
        bp = Blogpost(**{**_valid_blogpost_data(), "tags": ["x" * 64]})
        assert len(bp.tags[0]) == 64

    # Happy path

    def test_roundtrip(self):
        data = _valid_blogpost_data()
        bp = Blogpost(**data)
        assert bp.id == data["id"]
        assert bp.title == data["title"]
        assert bp.text == data["text"]
        assert bp.tags == data["tags"]
        assert bp.updated_at == data["updated_at"]
