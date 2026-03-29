from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RegisterIn(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SessionStartIn(APIModel):
    quiz_id: str = Field(min_length=1)


class AnswerIn(APIModel):
    question_number: int = Field(ge=1)
    chosen_answer: str = Field(min_length=1, max_length=1)
    response_time_ms: int = Field(gt=0, lt=600000)


class SyntheticStudentCreateIn(APIModel):
    email: EmailStr


class BulkStudentsIn(APIModel):
    students: list[SyntheticStudentCreateIn]


class SimAnswer(APIModel):
    question_number: int = Field(ge=1)
    chosen_answer: str = Field(min_length=1, max_length=1)
    response_time_ms: int = Field(gt=0, lt=600000)


class SimSession(APIModel):
    quiz_id: str = Field(min_length=1)
    answers: list[SimAnswer]


class SimStudent(APIModel):
    student_id: UUID
    sessions: list[SimSession]


class SimBatchIn(APIModel):
    students: list[SimStudent]


class DifficultyUpdateItem(APIModel):
    quiz_id: str = Field(min_length=1)
    question_number: int = Field(ge=1)
    difficulty: str


class DifficultyIn(APIModel):
    updates: list[DifficultyUpdateItem]


class TokenOut(APIModel):
    access_token: str
    token_type: str = "bearer"
    student_id: UUID


class QuestionOut(APIModel):
    question_number: int
    question_text: str
    choice_a: str
    choice_b: str
    choice_c: str | None = None
    choice_d: str | None = None
    choice_e: str | None = None
    choice_f: str | None = None


class QuizSummaryOut(APIModel):
    id: str
    display_name: str
    question_count: int


class QuizDetailOut(APIModel):
    id: str
    display_name: str
    questions: list[QuestionOut]


class SessionStartOut(APIModel):
    session_id: UUID
    question: QuestionOut
    question_number: int
    total: int


class AnswerOut(APIModel):
    done: bool
    question: QuestionOut | None = None
    question_number: int | None = None
    total: int | None = None
    session_id: UUID | None = None


class QuestionResultOut(APIModel):
    question_number: int
    chosen_answer: str
    is_correct: bool
    response_time_ms: int
    difficulty: str | None = None
    answered_at: datetime


class ResultOut(APIModel):
    total: int
    correct: int
    accuracy: float
    by_difficulty: dict[str, dict[str, int | float | None]]
    by_question: list[QuestionResultOut]


class SessionHistoryOut(APIModel):
    session_id: UUID
    quiz_id: str
    display_name: str
    started_at: datetime
    ended_at: datetime | None = None
    total: int
    correct: int
    accuracy: float


class ImportOut(APIModel):
    quizzes_created: int
    questions_inserted: int
    questions_skipped: int


class SyntheticStudentOut(APIModel):
    email: EmailStr
    id: UUID


class SimBatchOut(APIModel):
    sessions_created: int
    answers_inserted: int
    errors: list[str]


class DifficultyOut(APIModel):
    updated: int
