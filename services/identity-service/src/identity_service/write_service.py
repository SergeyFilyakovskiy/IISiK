from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.database import Database
from shared.errors import DomainError, ErrorCode

from .models import Student, User
from .read_schemas import StudentDTO


class IdentityWriteService:
    def __init__(self, database: Database) -> None:
        self.database = database

    async def update_student_profile(
        self,
        user_id: UUID,
        education_level: str | None = None,
        learning_goal: str | None = None,
        timezone: str | None = None,
    ) -> StudentDTO:
        async with self.database.session() as session:
            user = await session.scalar(
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.role), selectinload(User.student))
            )
            if user is None:
                raise DomainError(ErrorCode.NOT_FOUND, "User not found")
            if user.role.code != "STUDENT":
                raise DomainError(ErrorCode.FORBIDDEN, "User is not a student")
            if user.student is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Student profile not found")

            student = user.student
            if education_level is not None:
                student.education_level = education_level
            if learning_goal is not None:
                student.learning_goal = learning_goal
            if timezone is not None:
                student.timezone = timezone
            await session.commit()
            await session.refresh(student)
            return self.to_dto(student)

    @staticmethod
    def to_dto(student: Student) -> StudentDTO:
        return StudentDTO(
            id=student.id,
            user_id=student.user_id,
            education_level=student.education_level,
            learning_goal=student.learning_goal,
            timezone=student.timezone,
            status=student.status,
        )
