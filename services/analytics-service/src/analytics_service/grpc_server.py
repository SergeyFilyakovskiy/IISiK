from datetime import date
from functools import wraps

import grpc.aio
from analytics.v1 import analytics_pb2, analytics_pb2_grpc

from shared.auth import Role, require_role
from shared.errors import DomainError, ErrorCode
from shared.grpc import abort_with_domain_error, extract_principal, observe_rpc

from .service import AnalyticsService


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

    return observe_rpc(wrapper)


class AnalyticsServicer(analytics_pb2_grpc.AnalyticsServiceServicer):
    def __init__(self, service: AnalyticsService) -> None:
        self.service = service

    @rpc_handler
    async def GetReport(self, request, context):
        actor = extract_principal(context.invocation_metadata())
        require_role(actor, Role.ADMIN)
        report = await self.service.get_report(
            date.fromisoformat(request.period_from), date.fromisoformat(request.period_to)
        )
        return analytics_pb2.AnalyticsReport(
            period_from=report.period_from.isoformat(),
            period_to=report.period_to.isoformat(),
            lessons_completed=report.lessons_completed,
            bookings_created=report.bookings_created,
            revenue=str(report.revenue),
            avg_rating=str(report.avg_rating),
            teachers=[
                analytics_pb2.TeacherMetric(
                    teacher_id=str(item.teacher_id),
                    period_date=item.period_date.isoformat(),
                    lessons_completed=item.lessons_completed,
                    revenue=str(item.revenue),
                    avg_rating=str(item.avg_rating),
                    reviews_count=item.reviews_count,
                )
                for item in report.teachers
            ],
        )


def create_grpc_server(service: AnalyticsService, port: int):
    server = grpc.aio.server()
    analytics_pb2_grpc.add_AnalyticsServiceServicer_to_server(AnalyticsServicer(service), server)
    server.add_insecure_port(f"[::]:{port}")
    return server
