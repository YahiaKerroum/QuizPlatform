import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import verify_database_connection
from .routers.admin import router as admin_router
from .routers.auth import router as auth_router
from .routers.quizzes import router as quizzes_router
from .routers.sessions import router as sessions_router

app = FastAPI(title="Adaptive Quiz Platform API")

_DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "https://quiz-platform-ie9w.vercel.app",
]
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
_cors_allowed_origins = [origin.strip() for origin in _cors_env.split(",") if origin.strip()] or _DEFAULT_CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(quizzes_router, prefix="/quizzes", tags=["quizzes"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.on_event("startup")
async def startup_check() -> None:
    await verify_database_connection()
