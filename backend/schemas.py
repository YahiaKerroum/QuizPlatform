from datetime import datetime
from uuid import UUID
from typing import Literal

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
    adaptive: bool = False


class AnswerIn(APIModel):
    question_number: int = Field(ge=1)
    chosen_answer: Literal["a", "b", "c", "d", "e", "f"]
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
    difficulty: Literal["easy", "medium", "hard"]


class DifficultyIn(APIModel):
    updates: list[DifficultyUpdateItem]


class TokenOut(APIModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    student_id: UUID


class AuthMeOut(APIModel):
    email: EmailStr
    is_admin: bool


class QuestionOut(APIModel):
    question_number: int
    question_text: str
    question_image_url: str | None = None
    choice_a: str
    choice_a_image_url: str | None = None
    choice_b: str
    choice_b_image_url: str | None = None
    choice_c: str | None = None
    choice_c_image_url: str | None = None
    choice_d: str | None = None
    choice_d_image_url: str | None = None
    choice_e: str | None = None
    choice_e_image_url: str | None = None
    choice_f: str | None = None
    choice_f_image_url: str | None = None


class AdminQuestionIn(APIModel):
    question_number: int = Field(ge=1)
    question_text: str = Field(min_length=1)
    question_image_url: str | None = None
    choice_a: str = Field(min_length=1)
    choice_a_image_url: str | None = None
    choice_b: str = Field(min_length=1)
    choice_b_image_url: str | None = None
    choice_c: str | None = None
    choice_c_image_url: str | None = None
    choice_d: str | None = None
    choice_d_image_url: str | None = None
    choice_e: str | None = None
    choice_e_image_url: str | None = None
    choice_f: str | None = None
    choice_f_image_url: str | None = None
    correct_answer: Literal["a", "b", "c", "d", "e", "f"]
    difficulty: Literal["easy", "medium", "hard"] | None = None


class ModuleOut(APIModel):
    id: str
    display_name: str
    description: str | None = None
    quiz_count: int = 0


class QuizSummaryOut(APIModel):
    id: str
    display_name: str
    module_id: str | None = None
    module_display_name: str | None = None
    question_count: int


class QuizDetailOut(APIModel):
    id: str
    display_name: str
    module_id: str | None = None
    module_display_name: str | None = None
    questions: list[QuestionOut]


class AdminQuizDetailOut(APIModel):
    id: str
    display_name: str
    module_id: str | None = None
    module_display_name: str | None = None
    questions: list[AdminQuestionIn]


class SessionStartOut(APIModel):
    session_id: UUID
    question: QuestionOut
    question_number: int
    total: int
    is_adaptive: bool = False


class AnswerOut(APIModel):
    done: bool
    question: QuestionOut | None = None
    question_number: int | None = None
    total: int | None = None
    session_id: UUID | None = None
    predicted_level: str | None = None
    confidence: float | None = None


class QuestionResultOut(APIModel):
    question_number: int
    question_text: str
    question_image_url: str | None = None
    chosen_answer: str
    correct_answer: str
    chosen_answer_text: str | None = None
    chosen_answer_image_url: str | None = None
    correct_answer_text: str
    correct_answer_image_url: str | None = None
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
    is_adaptive: bool = False


class ImportOut(APIModel):
    quizzes_created: int
    questions_inserted: int
    questions_skipped: int


class ModuleCreateIn(APIModel):
    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    description: str | None = None


class ModuleUpdateIn(APIModel):
    display_name: str = Field(min_length=1)
    description: str | None = None


class QuizUpsertIn(APIModel):
    id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    module_id: str | None = None
    questions: list[AdminQuestionIn] = Field(min_length=1)


class ModuleWithQuizzesOut(APIModel):
    id: str
    display_name: str
    description: str | None = None
    quizzes: list[QuizSummaryOut]


class SyntheticStudentOut(APIModel):
    email: EmailStr
    id: UUID


class ProfileRoleSetIn(APIModel):
    email: EmailStr
    role: Literal["student", "admin"]


class ProfileRoleOut(APIModel):
    email: EmailStr
    role: Literal["student", "admin"]


class SimBatchOut(APIModel):
    sessions_created: int
    answers_inserted: int
    errors: list[str]


class DifficultyOut(APIModel):
    updated: int


class AdminAccessOut(APIModel):
    allowed: bool
    email: EmailStr
