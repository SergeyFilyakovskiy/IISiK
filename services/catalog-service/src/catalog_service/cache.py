import hashlib
import json
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from shared.cache import RedisJsonCache

from .schemas import (
    PageDTO,
    RatingDTO,
    SubjectDTO,
    TeacherDTO,
    TeacherFilterDTO,
    TeacherSubjectDTO,
)


def subject_from_dict(data) -> SubjectDTO:
    return SubjectDTO(
        id=UUID(data["id"]),
        name=data["name"],
        description=data["description"],
        is_active=data["is_active"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def teacher_from_dict(data) -> TeacherDTO:
    rating = data["rating"]
    return TeacherDTO(
        id=UUID(data["id"]),
        user_id=UUID(data["user_id"]),
        about=data["about"],
        experience_years=data["experience_years"],
        price_per_lesson=Decimal(data["price_per_lesson"]),
        currency=data["currency"],
        profile_status=data["profile_status"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        subjects=[
            TeacherSubjectDTO(
                subject=subject_from_dict(link["subject"]),
                proficiency_level=link["proficiency_level"],
            )
            for link in data["subjects"]
        ],
        rating=RatingDTO(
            teacher_id=UUID(rating["teacher_id"]),
            avg_rating=Decimal(rating["avg_rating"]),
            reviews_count=rating["reviews_count"],
            updated_at=datetime.fromisoformat(rating["updated_at"]),
        )
        if rating
        else None,
    )


class CatalogCache:
    def __init__(self, cache: RedisJsonCache) -> None:
        self.cache = cache

    async def _suffix(self, value) -> str:
        version = await self.cache.version()
        normalized = json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))
        digest = hashlib.sha256(normalized.encode()).hexdigest()
        return f"v{version}:{digest}"

    async def get_teacher(self, teacher_id: UUID, loader) -> TeacherDTO | None:
        suffix = await self._suffix(f"teacher:{teacher_id}")
        value = await self.cache.get_or_load(suffix, lambda: self._serialize(loader, teacher=True))
        return teacher_from_dict(value) if value is not None else None

    async def get_subject(self, subject_id: UUID, loader) -> SubjectDTO | None:
        suffix = await self._suffix(f"subject:{subject_id}")
        value = await self.cache.get_or_load(suffix, lambda: self._serialize(loader))
        return subject_from_dict(value) if value is not None else None

    async def list_subjects(self, filters: dict, loader) -> list[SubjectDTO]:
        suffix = await self._suffix({"subjects": filters})
        values = await self.cache.get_or_load(suffix, loader)
        return [subject_from_dict(value) for value in values]

    async def list_teachers(self, filters: TeacherFilterDTO, page: int, page_size: int, loader):
        suffix = await self._suffix(
            {"teachers": asdict(filters), "page": page, "page_size": page_size}
        )
        value = await self.cache.get_or_load(suffix, loader)
        return PageDTO(
            items=[teacher_from_dict(item) for item in value["items"]],
            page=value["page"],
            page_size=value["page_size"],
            total_items=value["total_items"],
            total_pages=value["total_pages"],
        )

    async def invalidate(self) -> None:
        await self.cache.bump_version()

    @staticmethod
    async def _serialize(loader, teacher: bool = False):
        value = await loader()
        return asdict(value) if value is not None else None
