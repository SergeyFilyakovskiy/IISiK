from datetime import datetime, time
from decimal import Decimal
from functools import wraps
from uuid import UUID

import grpc.aio
from scheduling.v1 import scheduling_pb2, scheduling_pb2_grpc

from shared.errors import DomainError, ErrorCode
from shared.events import publish_event
from shared.grpc import abort_with_domain_error, extract_principal
from shared.kafka import KafkaEventProducer

from .workflows import SchedulingWorkflowService


def rpc_handler(func):
    @wraps(func)
    async def wrapper(self, request, context):
        try:
            return await func(self, request, context)
        except DomainError as error:
            await abort_with_domain_error(context, error)
        except ValueError as error:
            await abort_with_domain_error(
                context, DomainError(ErrorCode.VALIDATION_ERROR, str(error))
            )

    return wrapper


def slot_to_proto(dto):
    return scheduling_pb2.ScheduleSlot(
        id=str(dto.id),
        teacher_id=str(dto.teacher_id),
        weekday=dto.weekday,
        start_time=dto.start_time.isoformat(),
        end_time=dto.end_time.isoformat(),
        is_active=dto.is_active,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )


def lesson_to_proto(dto):
    message = scheduling_pb2.Lesson(
        id=str(dto.id),
        teacher_id=str(dto.teacher_id),
        subject_id=str(dto.subject_id),
        start_at=dto.start_at.isoformat(),
        duration_minutes=dto.duration_minutes,
        status=dto.status,
        price=str(dto.price),
        currency=dto.currency,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )
    if dto.schedule_slot_id is not None:
        message.schedule_slot_id = str(dto.schedule_slot_id)
    return message


class SchedulingServicer(scheduling_pb2_grpc.SchedulingServiceServicer):
    def __init__(self, workflows: SchedulingWorkflowService, events: KafkaEventProducer) -> None:
        self.workflows = workflows
        self.service = workflows.service
        self.events = events

    async def _publish(self, event_type: str, lesson) -> None:
        await publish_event(
            self.events,
            event_type,
            event_type,
            lesson.id,
            {
                "lesson_id": str(lesson.id),
                "teacher_id": str(lesson.teacher_id),
                "subject_id": str(lesson.subject_id),
                "status": lesson.status,
            },
        )

    @rpc_handler
    async def GetLesson(self, request, context):
        lesson = await self.service.get_lesson(UUID(request.lesson_id))
        response = scheduling_pb2.GetLessonResponse()
        if lesson is not None:
            response.lesson.CopyFrom(lesson_to_proto(lesson))
        return response

    @rpc_handler
    async def ListSchedule(self, request, context):
        slots = await self.service.list_schedule(UUID(request.teacher_id))
        return scheduling_pb2.ListScheduleResponse(items=[slot_to_proto(item) for item in slots])

    @rpc_handler
    async def ListAvailableLessons(self, request, context):
        lessons = await self.service.list_available_lessons(
            teacher_id=UUID(request.teacher_id) if request.HasField("teacher_id") else None,
            subject_id=UUID(request.subject_id) if request.HasField("subject_id") else None,
            start_from=datetime.fromisoformat(request.start_from)
            if request.HasField("start_from")
            else None,
            end_to=datetime.fromisoformat(request.end_to) if request.HasField("end_to") else None,
            min_price=Decimal(request.min_price) if request.HasField("min_price") else None,
            max_price=Decimal(request.max_price) if request.HasField("max_price") else None,
            sort_by=request.sort_by,
            sort_direction=request.sort_direction,
        )
        return scheduling_pb2.ListLessonsResponse(items=[lesson_to_proto(item) for item in lessons])

    @rpc_handler
    async def CreateScheduleSlot(self, request, context):
        slot = await self.workflows.create_schedule_slot(
            extract_principal(context.invocation_metadata()),
            UUID(request.teacher_id),
            request.weekday,
            time.fromisoformat(request.start_time),
            time.fromisoformat(request.end_time),
        )
        return slot_to_proto(slot)

    @rpc_handler
    async def UpdateScheduleSlot(self, request, context):
        changes = {}
        for field in ("weekday", "is_active"):
            if request.HasField(field):
                changes[field] = getattr(request, field)
        for field in ("start_time", "end_time"):
            if request.HasField(field):
                changes[field] = time.fromisoformat(getattr(request, field))
        slot = await self.workflows.update_schedule_slot(
            extract_principal(context.invocation_metadata()), UUID(request.slot_id), **changes
        )
        return slot_to_proto(slot)

    @rpc_handler
    async def DeleteScheduleSlot(self, request, context):
        deleted = await self.workflows.delete_schedule_slot(
            extract_principal(context.invocation_metadata()), UUID(request.slot_id)
        )
        return scheduling_pb2.DeleteScheduleSlotResponse(deleted=deleted)

    @rpc_handler
    async def PublishLesson(self, request, context):
        lesson = await self.workflows.publish_lesson(
            extract_principal(context.invocation_metadata()),
            UUID(request.teacher_id),
            UUID(request.subject_id),
            UUID(request.schedule_slot_id) if request.HasField("schedule_slot_id") else None,
            datetime.fromisoformat(request.start_at),
            request.duration_minutes,
        )
        await self._publish("scheduling.lesson.created", lesson)
        return lesson_to_proto(lesson)

    @rpc_handler
    async def CancelLesson(self, request, context):
        lesson = await self.workflows.cancel_lesson(
            extract_principal(context.invocation_metadata()),
            UUID(request.lesson_id),
            request.reason if request.HasField("reason") else None,
        )
        await self._publish("scheduling.lesson.cancelled", lesson)
        return lesson_to_proto(lesson)

    @rpc_handler
    async def RescheduleLesson(self, request, context):
        lesson = await self.workflows.reschedule_lesson(
            extract_principal(context.invocation_metadata()),
            UUID(request.lesson_id),
            datetime.fromisoformat(request.new_start_at),
        )
        return lesson_to_proto(lesson)

    @rpc_handler
    async def ReserveLesson(self, request, context):
        return lesson_to_proto(await self.service.reserve_lesson(UUID(request.lesson_id)))

    @rpc_handler
    async def ReleaseLesson(self, request, context):
        return lesson_to_proto(await self.service.release_lesson(UUID(request.lesson_id)))

    @rpc_handler
    async def MarkLessonBooked(self, request, context):
        return lesson_to_proto(await self.service.mark_lesson_booked(UUID(request.lesson_id)))

    @rpc_handler
    async def CompleteLesson(self, request, context):
        lesson = await self.service.complete_lesson(UUID(request.lesson_id))
        await self._publish("scheduling.lesson.completed", lesson)
        return lesson_to_proto(lesson)


def create_grpc_server(workflows: SchedulingWorkflowService, port: int, events: KafkaEventProducer):
    server = grpc.aio.server()
    scheduling_pb2_grpc.add_SchedulingServiceServicer_to_server(
        SchedulingServicer(workflows, events), server
    )
    server.add_insecure_port(f"[::]:{port}")
    return server
