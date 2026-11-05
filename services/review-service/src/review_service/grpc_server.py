from functools import wraps
from uuid import UUID

import grpc.aio
from review.v1 import review_pb2, review_pb2_grpc

from shared.errors import DomainError, ErrorCode
from shared.events import publish_event
from shared.grpc import abort_with_domain_error, extract_principal
from shared.kafka import KafkaEventProducer

from .workflows import ReviewWorkflowService


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


def review_to_proto(dto):
    message = review_pb2.Review(
        id=str(dto.id),
        lesson_id=str(dto.lesson_id),
        student_id=str(dto.student_id),
        teacher_id=str(dto.teacher_id),
        rating=dto.rating,
        created_at=dto.created_at.isoformat(),
        updated_at=dto.updated_at.isoformat(),
    )
    if dto.comment is not None:
        message.comment = dto.comment
    return message


class ReviewServicer(review_pb2_grpc.ReviewServiceServicer):
    def __init__(self, workflows: ReviewWorkflowService, events: KafkaEventProducer) -> None:
        self.workflows = workflows
        self.service = workflows.service
        self.events = events

    @rpc_handler
    async def ListTeacherReviews(self, request, context):
        result = await self.service.list_teacher_reviews(
            UUID(request.teacher_id),
            request.page,
            request.page_size,
            request.min_rating if request.HasField("min_rating") else None,
            request.sort_by,
            request.sort_direction,
        )
        response = review_pb2.ReviewPage(
            page_info=review_pb2.PageInfo(
                page=result.page,
                page_size=result.page_size,
                total_items=result.total_items,
                total_pages=result.total_pages,
            )
        )
        response.items.extend(review_to_proto(item) for item in result.items)
        return response

    @rpc_handler
    async def CreateReview(self, request, context):
        review, average, count = await self.workflows.create_review(
            extract_principal(context.invocation_metadata()),
            UUID(request.lesson_id),
            request.rating,
            request.comment if request.HasField("comment") else None,
        )
        await publish_event(
            self.events,
            "review.created",
            "review.created",
            review.id,
            {
                "review_id": str(review.id),
                "lesson_id": str(review.lesson_id),
                "student_id": str(review.student_id),
                "teacher_id": str(review.teacher_id),
                "rating": review.rating,
                "average_rating": str(average),
                "reviews_count": count,
            },
        )
        return review_to_proto(review)


def create_grpc_server(workflows: ReviewWorkflowService, port: int, events: KafkaEventProducer):
    server = grpc.aio.server()
    review_pb2_grpc.add_ReviewServiceServicer_to_server(ReviewServicer(workflows, events), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
