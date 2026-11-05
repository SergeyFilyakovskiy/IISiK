from catalog.v1 import catalog_pb2, catalog_pb2_grpc

from shared.auth import CurrentUser
from shared.grpc import call_with_policy, create_channel


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

    async def get_teacher_by_user_id(self, user_id: str, actor: CurrentUser):
        response = await call_with_policy(
            self.stub.GetTeacherByUserId,
            catalog_pb2.GetTeacherByUserIdRequest(user_id=user_id),
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
