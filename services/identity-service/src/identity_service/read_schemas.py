from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StudentDTO:
    id: UUID
    user_id: UUID
    education_level: str | None
    learning_goal: str | None
    timezone: str | None
    status: str


@dataclass(frozen=True, slots=True)
class UserDTO:
    id: UUID
    email: str
    full_name: str
    role: str
    status: str
    student: StudentDTO | None
