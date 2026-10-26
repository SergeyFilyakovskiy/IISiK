from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.database import Database

from .models import Student, User
from .read_schemas import StudentDTO, UserDTO


class IdentityReadRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def get_user(self, user_id: UUID) -> UserDTO | None:
        async with self.database.session() as session:
            user = await session.scalar(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.role), selectinload(User.student))
            )
            if user is None:
                return None
            return UserDTO(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=user.role.code,
                status=user.status,
                student=self._to_student_dto(user.student),
            )

    async def get_student_by_user_id(self, user_id: UUID) -> StudentDTO | None:
        async with self.database.session() as session:
            student = await session.scalar(select(Student).where(Student.user_id == user_id))
            if student is None:
                return None
            return self._to_student_dto(student)

    @staticmethod
    def _to_student_dto(student: Student | None) -> StudentDTO | None:
        if student is None:
            return None
        return StudentDTO(
            id=student.id,
            user_id=student.user_id,
            education_level=student.education_level,
            learning_goal=student.learning_goal,
            timezone=student.timezone,
            status=student.status,
        )
