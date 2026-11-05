from datetime import datetime, time
from decimal import Decimal
from uuid import UUID

from shared.auth import CurrentUser, Role, require_role
from shared.errors import DomainError, ErrorCode

from .clients import CatalogClient
from .schemas import LessonDTO, ScheduleSlotDTO
from .service import SchedulingService


class SchedulingWorkflowService:
    def __init__(self, service: SchedulingService, catalog: CatalogClient) -> None:
        self.service = service
        self.catalog = catalog

    async def _require_teacher(self, actor: CurrentUser, teacher_id: UUID) -> None:
        require_role(actor, Role.TEACHER, admin_override=True)
        if actor.role is Role.ADMIN:
            return
        teacher = await self.catalog.get_teacher_by_user_id(str(actor.user_id), actor)
        if teacher is None or teacher.id != str(teacher_id):
            raise DomainError(ErrorCode.FORBIDDEN, "Teacher does not own this resource")

    async def create_schedule_slot(
        self,
        actor: CurrentUser,
        teacher_id: UUID,
        weekday: int,
        start_time: time,
        end_time: time,
    ) -> ScheduleSlotDTO:
        await self._require_teacher(actor, teacher_id)
        return await self.service.create_schedule_slot(teacher_id, weekday, start_time, end_time)

    async def update_schedule_slot(self, actor: CurrentUser, slot_id: UUID, **changes):
        slot = await self.service.get_schedule_slot(slot_id)
        if slot is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Schedule slot not found")
        await self._require_teacher(actor, slot.teacher_id)
        return await self.service.update_schedule_slot(slot_id, **changes)

    async def delete_schedule_slot(self, actor: CurrentUser, slot_id: UUID) -> bool:
        slot = await self.service.get_schedule_slot(slot_id)
        if slot is None:
            return False
        await self._require_teacher(actor, slot.teacher_id)
        return await self.service.delete_schedule_slot(slot_id)

    async def publish_lesson(
        self,
        actor: CurrentUser,
        teacher_id: UUID,
        subject_id: UUID,
        schedule_slot_id: UUID | None,
        start_at: datetime,
        duration_minutes: int,
    ) -> LessonDTO:
        await self._require_teacher(actor, teacher_id)
        teacher = await self.catalog.get_teacher(str(teacher_id), actor)
        subject = await self.catalog.get_subject(str(subject_id), actor)
        if teacher is None or subject is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Catalog data not found")
        if teacher.profile_status != "ACTIVE" or not subject.is_active:
            raise DomainError(ErrorCode.CONFLICT, "Teacher or subject is inactive")
        if not any(link.subject.id == str(subject_id) for link in teacher.subjects):
            raise DomainError(ErrorCode.VALIDATION_ERROR, "Teacher does not teach this subject")
        return await self.service.create_lesson(
            teacher_id,
            subject_id,
            schedule_slot_id,
            start_at,
            duration_minutes,
            Decimal(teacher.price_per_lesson),
            teacher.currency,
        )

    async def cancel_lesson(self, actor: CurrentUser, lesson_id: UUID, reason: str | None):
        lesson = await self.service.get_lesson(lesson_id)
        if lesson is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Lesson not found")
        await self._require_teacher(actor, lesson.teacher_id)
        if lesson.status != "AVAILABLE":
            raise DomainError(
                ErrorCode.CONFLICT, "A reserved or booked lesson must be cancelled via its booking"
            )
        return await self.service.cancel_lesson(lesson_id, reason)

    async def reschedule_lesson(self, actor: CurrentUser, lesson_id: UUID, new_start_at: datetime):
        lesson = await self.service.get_lesson(lesson_id)
        if lesson is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Lesson not found")
        await self._require_teacher(actor, lesson.teacher_id)
        return await self.service.reschedule_lesson(lesson_id, new_start_at)
