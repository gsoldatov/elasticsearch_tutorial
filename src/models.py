import ast
from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class DocumentCreate(BaseModel):
    text: str
    created_date: datetime
    rubrics: list[str]

    @field_validator("created_date", mode="before")
    @classmethod
    def ensure_utc(cls, v: str) -> datetime:
        # Добавление часового пояса UTC к меткам времени в формате,
        # представленном в тестовых данных
        dt = datetime.strptime(v, "%Y-%m-%d %H:%M:%S")
        return dt.replace(tzinfo=timezone.utc)

    @field_validator("rubrics", mode="before")
    @classmethod
    def parse_rubrics(cls, v: str | list) -> list[str]:
        if isinstance(v, str):
            return ast.literal_eval(v)
        return v
