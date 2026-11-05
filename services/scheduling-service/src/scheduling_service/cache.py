import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.cache import RedisJsonCache

from .schemas import LessonDTO


def lesson_from_dict(data) -> LessonDTO:
    return LessonDTO(
        id=UUID(data["id"]),
        teacher_id=UUID(data["teacher_id"]),
        subject_id=UUID(data["subject_id"]),
        schedule_slot_id=UUID(data["schedule_slot_id"]) if data["schedule_slot_id"] else None,
        start_at=datetime.fromisoformat(data["start_at"]),
        duration_minutes=data["duration_minutes"],
        status=data["status"],
        price=Decimal(data["price"]),
        currency=data["currency"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


class SchedulingCache:
    def __init__(self, cache: RedisJsonCache) -> None:
        self.cache = cache

    async def list_available(self, filters: dict, loader) -> list[LessonDTO]:
        version = await self.cache.version()
        normalized = json.dumps(filters, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        values = await self.cache.get_or_load(f"v{version}:available:{digest}", loader)
        return [lesson_from_dict(value) for value in values]

    async def invalidate(self) -> None:
        await self.cache.bump_version()

    @staticmethod
    def serialize(lessons: list[LessonDTO]) -> list[dict]:
        return [asdict(lesson) for lesson in lessons]
