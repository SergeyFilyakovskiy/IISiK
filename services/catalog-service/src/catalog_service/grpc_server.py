from decimal import Decimal
from functools import wraps
from uuid import UUID

import grpc.aio
from catalog.v1 import catalog_pb2, catalog_pb2_grpc

from shared.errors import DomainError, ErrorCode
from shared.grpc import abort_with_domain_error, extract_principal

from .schemas import TeacherFilterDTO
from .service import CatalogService


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


def subject_to_proto(dto):
    message = catalog_pb2.Subject(
        id=str(dto.id),
        name=dto.name,
        is_active=dto.is_active,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )
    if dto.description is not None:
        message.description = dto.description
    return message


def teacher_to_proto(dto):
    message = catalog_pb2.Teacher(
        id=str(dto.id),
        user_id=str(dto.user_id),
        experience_years=dto.experience_years,
        price_per_lesson=str(dto.price_per_lesson),
        currency=dto.currency,
        profile_status=dto.profile_status,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )
    if dto.about is not None:
        message.about = dto.about
    for link in dto.subjects:
        item = catalog_pb2.TeacherSubject(subject=subject_to_proto(link.subject))
        if link.proficiency_level is not None:
            item.proficiency_level = link.proficiency_level
        message.subjects.append(item)
    if dto.rating is not None:
        message.rating.CopyFrom(
            catalog_pb2.Rating(
                teacher_id=str(dto.rating.teacher_id),
                avg_rating=str(dto.rating.avg_rating),
                reviews_count=dto.rating.reviews_count,
                updated_at=dto.rating.updated_at.isoformat(),
            )
        )
    return message


class CatalogServicer(catalog_pb2_grpc.CatalogServiceServicer):
    def __init__(self, service: CatalogService) -> None:
        self.service = service

    @rpc_handler
    async def GetTeacher(self, request, context):
        teacher = await self.service.get_teacher(UUID(request.teacher_id))
        response = catalog_pb2.GetTeacherResponse()
        if teacher is not None:
            response.teacher.CopyFrom(teacher_to_proto(teacher))
        return response

    @rpc_handler
    async def GetTeacherByUserId(self, request, context):
        teacher = await self.service.get_teacher_by_user_id(UUID(request.user_id))
        response = catalog_pb2.GetTeacherResponse()
        if teacher is not None:
            response.teacher.CopyFrom(teacher_to_proto(teacher))
        return response

    @rpc_handler
    async def ListTeachers(self, request, context):
        result = await self.service.list_teachers(
            TeacherFilterDTO(
                subject_id=UUID(request.subject_id) if request.HasField("subject_id") else None,
                min_rating=Decimal(request.min_rating) if request.HasField("min_rating") else None,
                max_price=Decimal(request.max_price) if request.HasField("max_price") else None,
                sort_by=request.sort_by,
                sort_direction=request.sort_direction,
            ),
            request.page,
            request.page_size,
        )
        response = catalog_pb2.TeacherPage(
            page_info=catalog_pb2.PageInfo(
                page=result.page,
                page_size=result.page_size,
                total_items=result.total_items,
                total_pages=result.total_pages,
            )
        )
        response.items.extend(teacher_to_proto(item) for item in result.items)
        return response

    @rpc_handler
    async def GetSubject(self, request, context):
        subject = await self.service.get_subject(UUID(request.subject_id))
        response = catalog_pb2.GetSubjectResponse()
        if subject is not None:
            response.subject.CopyFrom(subject_to_proto(subject))
        return response

    @rpc_handler
    async def ListSubjects(self, request, context):
        subjects = await self.service.list_subjects(
            search=request.search if request.HasField("search") else None,
            is_active=request.is_active if request.HasField("is_active") else None,
            sort_direction=request.sort_direction,
        )
        return catalog_pb2.ListSubjectsResponse(items=[subject_to_proto(item) for item in subjects])

    @rpc_handler
    async def CreateTeacherProfile(self, request, context):
        teacher = await self.service.create_teacher_profile(
            extract_principal(context.invocation_metadata()),
            request.about if request.HasField("about") else None,
            request.experience_years,
            Decimal(request.price_per_lesson),
            request.currency,
            [UUID(item) for item in request.subject_ids],
        )
        return teacher_to_proto(teacher)

    @rpc_handler
    async def UpdateTeacherProfile(self, request, context):
        changes = {}
        for field in ("about", "experience_years", "currency", "profile_status"):
            if request.HasField(field):
                changes[field] = getattr(request, field)
        if request.HasField("price_per_lesson"):
            changes["price_per_lesson"] = Decimal(request.price_per_lesson)
        teacher = await self.service.update_teacher_profile(
            UUID(request.teacher_id), extract_principal(context.invocation_metadata()), **changes
        )
        return teacher_to_proto(teacher)

    @rpc_handler
    async def AddTeacherSubject(self, request, context):
        teacher = await self.service.add_teacher_subject(
            UUID(request.teacher_id),
            UUID(request.subject_id),
            request.proficiency_level if request.HasField("proficiency_level") else None,
            extract_principal(context.invocation_metadata()),
        )
        return teacher_to_proto(teacher)

    @rpc_handler
    async def RemoveTeacherSubject(self, request, context):
        teacher = await self.service.remove_teacher_subject(
            UUID(request.teacher_id),
            UUID(request.subject_id),
            extract_principal(context.invocation_metadata()),
        )
        return teacher_to_proto(teacher)

    @rpc_handler
    async def CreateSubject(self, request, context):
        subject = await self.service.create_subject(
            extract_principal(context.invocation_metadata()),
            request.name,
            request.description if request.HasField("description") else None,
            request.is_active,
        )
        return subject_to_proto(subject)

    @rpc_handler
    async def UpdateSubject(self, request, context):
        changes = {
            field: getattr(request, field)
            for field in ("name", "description", "is_active")
            if request.HasField(field)
        }
        subject = await self.service.update_subject(
            UUID(request.subject_id), extract_principal(context.invocation_metadata()), **changes
        )
        return subject_to_proto(subject)


def create_grpc_server(service: CatalogService, port: int):
    server = grpc.aio.server()
    catalog_pb2_grpc.add_CatalogServiceServicer_to_server(CatalogServicer(service), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
