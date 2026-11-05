from catalog.v1 import catalog_pb2, catalog_pb2_grpc
from payment.v1 import payment_pb2, payment_pb2_grpc
from scheduling.v1 import scheduling_pb2, scheduling_pb2_grpc

from shared.auth import CurrentUser
from shared.grpc import call_with_policy, create_channel


class SchedulingClient:
    def __init__(self, address: str, timeout: float = 5.0) -> None:
        self.channel = create_channel(address)
        self.stub = scheduling_pb2_grpc.SchedulingServiceStub(self.channel)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()

    async def get_lesson(self, lesson_id: str, actor: CurrentUser):
        response = await call_with_policy(
            self.stub.GetLesson,
            scheduling_pb2.GetLessonRequest(lesson_id=lesson_id),
            timeout=self.timeout,
            retry=True,
            principal=actor,
        )
        return response.lesson if response.HasField("lesson") else None

    async def _transition(self, call, lesson_id: str, actor: CurrentUser, retry: bool = False):
        return await call_with_policy(
            call,
            scheduling_pb2.LessonTransitionRequest(lesson_id=lesson_id),
            timeout=self.timeout,
            retry=retry,
            principal=actor,
        )

    async def reserve(self, lesson_id: str, actor: CurrentUser):
        return await self._transition(self.stub.ReserveLesson, lesson_id, actor)

    async def release(self, lesson_id: str, actor: CurrentUser):
        return await self._transition(self.stub.ReleaseLesson, lesson_id, actor, retry=True)

    async def mark_booked(self, lesson_id: str, actor: CurrentUser):
        return await self._transition(self.stub.MarkLessonBooked, lesson_id, actor, retry=True)

    async def complete(self, lesson_id: str, actor: CurrentUser):
        return await self._transition(self.stub.CompleteLesson, lesson_id, actor, retry=True)

    async def cancel(self, lesson_id: str, reason: str | None, actor: CurrentUser):
        request = scheduling_pb2.CancelLessonRequest(lesson_id=lesson_id)
        if reason is not None:
            request.reason = reason
        return await call_with_policy(
            self.stub.CancelLesson,
            request,
            timeout=self.timeout,
            principal=actor,
        )


class PaymentClient:
    def __init__(self, address: str, timeout: float = 5.0) -> None:
        self.channel = create_channel(address)
        self.stub = payment_pb2_grpc.PaymentServiceStub(self.channel)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()

    async def process(self, booking, payment_method: str, key: str, actor: CurrentUser):
        return await call_with_policy(
            self.stub.ProcessPayment,
            payment_pb2.ProcessPaymentRequest(
                booking_id=str(booking.id),
                student_id=str(booking.student_id),
                teacher_id=str(booking.teacher_id),
                amount=str(booking.price),
                currency=booking.currency,
                payment_method=payment_method,
                idempotency_key=key,
            ),
            timeout=self.timeout,
            principal=actor,
        )

    async def get_by_booking(self, booking_id: str, actor: CurrentUser):
        response = await call_with_policy(
            self.stub.GetPaymentByBooking,
            payment_pb2.GetPaymentByBookingRequest(booking_id=booking_id),
            timeout=self.timeout,
            retry=True,
            principal=actor,
        )
        return response.payment if response.HasField("payment") else None

    async def refund(self, payment_id: str, reason: str | None, actor: CurrentUser):
        request = payment_pb2.RefundPaymentRequest(payment_id=payment_id)
        if reason is not None:
            request.reason = reason
        return await call_with_policy(
            self.stub.RefundPayment,
            request,
            timeout=self.timeout,
            retry=True,
            principal=actor,
        )


class CatalogClient:
    def __init__(self, address: str, timeout: float = 5.0) -> None:
        self.channel = create_channel(address)
        self.stub = catalog_pb2_grpc.CatalogServiceStub(self.channel)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()

    async def get_teacher(self, teacher_id: str, actor: CurrentUser):
        response = await call_with_policy(
            self.stub.GetTeacher,
            catalog_pb2.GetTeacherRequest(teacher_id=teacher_id),
            timeout=self.timeout,
            retry=True,
            principal=actor,
        )
        return response.teacher if response.HasField("teacher") else None

    async def get_subject(self, subject_id: str, actor: CurrentUser):
        response = await call_with_policy(
            self.stub.GetSubject,
            catalog_pb2.GetSubjectRequest(subject_id=subject_id),
            timeout=self.timeout,
            retry=True,
            principal=actor,
        )
        return response.subject if response.HasField("subject") else None


def booking_from_proto(message) -> object:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from .schemas import BookingDTO

    def optional_datetime(name):
        return datetime.fromisoformat(getattr(message, name)) if message.HasField(name) else None

    return BookingDTO(
        id=UUID(message.id),
        lesson_id=UUID(message.lesson_id),
        student_id=UUID(message.student_id),
        teacher_id=UUID(message.teacher_id),
        subject_id=UUID(message.subject_id),
        status=message.status,
        price=Decimal(message.price),
        currency=message.currency,
        created_at=datetime.fromisoformat(message.created_at),
        updated_at=datetime.fromisoformat(message.updated_at),
        paid_at=optional_datetime("paid_at"),
        completed_at=optional_datetime("completed_at"),
        cancelled_at=optional_datetime("cancelled_at"),
        cancel_reason=message.cancel_reason if message.HasField("cancel_reason") else None,
    )
