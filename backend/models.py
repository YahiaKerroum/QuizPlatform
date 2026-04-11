from pydantic import BaseModel, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

class Module(BaseModel):
    id: str
    display_name: str
    description: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Quiz(BaseModel):
    id: str
    display_name: str
    module_id: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Question(BaseModel):
    quiz_id: str
    question_number: int
    question_text: str
    question_image_url: Optional[str] = None
    choice_a: str
    choice_a_image_url: Optional[str] = None
    choice_b: str
    choice_b_image_url: Optional[str] = None
    choice_c: Optional[str] = None
    choice_c_image_url: Optional[str] = None
    choice_d: Optional[str] = None
    choice_d_image_url: Optional[str] = None
    choice_e: Optional[str] = None
    choice_e_image_url: Optional[str] = None
    choice_f: Optional[str] = None
    choice_f_image_url: Optional[str] = None
    correct_answer: str
    difficulty: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class Student(BaseModel):
    id: uuid.UUID
    email: str
    password_hash: Optional[str] = None
    is_synthetic: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Profile(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str = "student"
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Session(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    quiz_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class Answer(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    quiz_id: str
    question_number: int
    chosen_answer: str
    is_correct: bool
    response_time_ms: int
    answered_at: datetime
    model_config = ConfigDict(from_attributes=True)
