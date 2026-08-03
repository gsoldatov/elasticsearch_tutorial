"""Тесты валидаторов query-параметров продаж."""

import pytest

from src.models.sales import validate_products_param, validate_region_param


# ── validate_region_param ──────────────────────────────────────────────────


class TestValidateRegionParam:
    def test_none_returns_none(self):
        assert validate_region_param(None) is None

    def test_single_region_ok(self):
        result = validate_region_param("Россия")
        assert result == "Россия"

    def test_multiple_regions_ok(self):
        result = validate_region_param("Россия, Германия, Франция")
        assert result == "Россия, Германия, Франция"

    def test_strips_whitespace(self):
        result = validate_region_param(" Россия ,  Германия ")
        assert result == " Россия ,  Германия "

    def test_empty_string_element_raises(self):
        with pytest.raises(ValueError, match="Длина каждого элемента region"):
            validate_region_param("Россия,,")

    def test_element_too_short_raises(self):
        with pytest.raises(ValueError, match="Длина каждого элемента region"):
            validate_region_param("")

    def test_element_too_long_raises(self):
        with pytest.raises(ValueError, match="Длина каждого элемента region"):
            validate_region_param("x" * 65)

    def test_too_many_elements_raises(self):
        with pytest.raises(ValueError, match="не более 10 элементов"):
            validate_region_param(",".join(str(i) for i in range(11)))


# ── validate_products_param ────────────────────────────────────────────────


class TestValidateProductsParam:
    def test_none_returns_none(self):
        assert validate_products_param(None) is None

    def test_single_product_ok(self):
        result = validate_products_param("ноутбук")
        assert result == "ноутбук"

    def test_multiple_products_ok(self):
        result = validate_products_param("ноутбук, телефон, планшет")
        assert result == "ноутбук, телефон, планшет"

    def test_element_too_long_raises(self):
        with pytest.raises(ValueError, match="Длина каждого элемента products"):
            validate_products_param("x" * 65)

    def test_too_many_elements_raises(self):
        with pytest.raises(ValueError, match="не более 10 элементов"):
            validate_products_param(",".join(str(i) for i in range(11)))
