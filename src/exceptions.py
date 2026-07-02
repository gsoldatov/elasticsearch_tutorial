import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import overload

from pydantic import ValidationError


class InternalValidationException(Exception):
    """Ошибка внутренней валидации — подменяет Pydantic ValidationError."""


@overload
def internal_validation[**P, R](
    func: Callable[P, Awaitable[R]],
) -> Callable[P, Awaitable[R]]: ...


@overload
def internal_validation[**P, R](func: Callable[P, R]) -> Callable[P, R]: ...


def internal_validation[**P, R](
    func: Callable[P, R],
) -> Callable[P, R] | Callable[P, Awaitable[R]]:
    """
    Декоратор: перехватывает Pydantic ValidationError
    и выбрасывает InternalValidationException.
    """

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                raise InternalValidationException(str(e)) from e

        return async_wrapper

    else:

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except ValidationError as e:
                raise InternalValidationException(str(e)) from e

        return sync_wrapper
