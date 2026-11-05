from identity.v1 import identity_pb2, identity_pb2_grpc

from shared.grpc import call_with_policy, create_channel


class IdentityClient:
    def __init__(self, address: str, timeout: float = 5.0) -> None:
        self.channel = create_channel(address)
        self.stub = identity_pb2_grpc.IdentityServiceStub(self.channel)
        self.timeout = timeout

    async def close(self) -> None:
        await self.channel.close()

    async def get_student(self, student_id: str):
        response = await call_with_policy(
            self.stub.GetStudent,
            identity_pb2.GetStudentRequest(student_id=student_id),
            timeout=self.timeout,
            retry=True,
        )
        return response.student if response.HasField("student") else None
