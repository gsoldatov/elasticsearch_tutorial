"""Shared Pydantic validation mixins."""
from collections.abc import Iterable
from typing import Self, cast

from pydantic import BaseModel, model_validator


class AnyOf:
    """
    Mixin class with a model validator, which ensures
    that at least one field is not null.

    `__any_of_fields__` can be overridden to apply the check
    to a specific subset of attributes only.
    """
    __any_of_fields__: Iterable[str] | None = None

    @model_validator(mode="after")
    def validator(self) -> Self:
        checked_fields = tuple(
            self.__any_of_fields__
            or cast(type[BaseModel], self.__class__).model_fields.keys()
        )

        for attr in checked_fields:
            if getattr(self, attr, None) is not None:
                return self
        raise ValueError(
            f"At least one non-null field from {checked_fields} is required."
        )
