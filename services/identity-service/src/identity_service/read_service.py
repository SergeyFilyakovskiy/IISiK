from uuid import UUID

from shared.database import Database

from .read_schemas import StudentDTO, UserDTO
from .repositories import IdentityReadRepository


class IdentityReadService:
    def __init__(self, database: Database) -> None:
        self.repository = IdentityReadRepository(database)

    async def get_user(self, user_id: UUID) -> UserDTO | None:
        return await self.repository.get_user(user_id)

    async def get_student_by_user_id(self, user_id: UUID) -> StudentDTO | None:
        return await self.repository.get_student_by_user_id(user_id)
