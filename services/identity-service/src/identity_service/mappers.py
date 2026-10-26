from .models import User
from .schemas import StudentProfileResponse, UserResponse


def to_user_response(user: User) -> UserResponse:
    student = None
    if user.student is not None:
        student = StudentProfileResponse(
            id=user.student.id,
            education_level=user.student.education_level,
            learning_goal=user.student.learning_goal,
            timezone=user.student.timezone,
            status=user.student.status,
        )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.code,
        status=user.status,
        student=student,
    )
