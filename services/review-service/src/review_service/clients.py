from booking.v1 import booking_pb2, booking_pb2_grpc

from shared.auth import CurrentUser
from shared.grpc import call_with_policy, create_channel


class BookingClient:
    def __init__(self, address: str, timeout: float = 5.0) -> None:
        self.channel = create_channel(address)
        self.stub = booking_pb2_grpc.BookingServiceStub(self.channel)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()

    async def get_by_lesson(self, lesson_id: str, actor: CurrentUser):
        response = await call_with_policy(
            self.stub.GetBookingByLesson,
            booking_pb2.GetBookingByLessonRequest(lesson_id=lesson_id),
            timeout=self.timeout,
            retry=True,
            principal=actor,
        )
        return response.booking if response.HasField("booking") else None
