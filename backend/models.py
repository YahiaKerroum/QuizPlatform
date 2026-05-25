import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint
from sqlalchemy import Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    quizzes: Mapped[list["Quiz"]] = relationship(
        back_populates="module",
        lazy="raise",
        order_by="Quiz.display_name",
    )


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    module_id: Mapped[str | None] = mapped_column(
        ForeignKey("modules.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    questions: Mapped[list["Question"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Question.question_number",
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="quiz",
        lazy="raise",
    )
    module: Mapped["Module | None"] = relationship(
        back_populates="quizzes",
        lazy="raise",
    )


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint(
            "correct_answer IN ('a','b','c','d','e','f')",
            name="ck_questions_correct_answer",
        ),
        CheckConstraint(
            "difficulty IN ('easy','medium','hard')",
            name="ck_questions_difficulty",
        ),
    )

    quiz_id: Mapped[str] = mapped_column(
        ForeignKey("quizzes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_image_url: Mapped[str | None] = mapped_column(Text)
    choice_a: Mapped[str] = mapped_column(Text, nullable=False)
    choice_a_image_url: Mapped[str | None] = mapped_column(Text)
    choice_b: Mapped[str] = mapped_column(Text, nullable=False)
    choice_b_image_url: Mapped[str | None] = mapped_column(Text)
    choice_c: Mapped[str | None] = mapped_column(Text)
    choice_c_image_url: Mapped[str | None] = mapped_column(Text)
    choice_d: Mapped[str | None] = mapped_column(Text)
    choice_d_image_url: Mapped[str | None] = mapped_column(Text)
    choice_e: Mapped[str | None] = mapped_column(Text)
    choice_e_image_url: Mapped[str | None] = mapped_column(Text)
    choice_f: Mapped[str | None] = mapped_column(Text)
    choice_f_image_url: Mapped[str | None] = mapped_column(Text)
    correct_answer: Mapped[str] = mapped_column(String(1), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(Text)

    quiz: Mapped["Quiz"] = relationship(
        back_populates="questions",
        lazy="raise",
    )
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="question",
        lazy="raise",
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(Text)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="raise",
    )


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    quiz_id: Mapped[str] = mapped_column(ForeignKey("quizzes.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_adaptive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    student: Mapped["Student"] = relationship(
        back_populates="sessions",
        lazy="raise",
    )
    quiz: Mapped["Quiz"] = relationship(
        back_populates="sessions",
        lazy="raise",
    )
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="raise",
        order_by="Answer.question_number",
    )


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        ForeignKeyConstraint(
            ["quiz_id", "question_number"],
            ["questions.quiz_id", "questions.question_number"],
        ),
        CheckConstraint(
            "chosen_answer IN ('a','b','c','d','e','f')",
            name="ck_answers_chosen_answer",
        ),
        CheckConstraint(
            "response_time_ms > 0 AND response_time_ms < 600000",
            name="ck_answers_response_time",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    quiz_id: Mapped[str] = mapped_column(Text, nullable=False)
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chosen_answer: Mapped[str] = mapped_column(String(1), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped["Session"] = relationship(
        back_populates="answers",
        lazy="raise",
    )
    question: Mapped["Question"] = relationship(
        back_populates="answers",
        lazy="raise",
    )
