import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import settings as _settings
from .auth import router as auth_router
from .catalog import router as catalog_router
from .eligibility import router as eligibility_router
from .recommendations import router as recommendations_router
from .profiles import router as profile_router
from .knowledge import router as knowledge_router
from .assistant import router as assistant_router
from .guidance import router as guidance_router
from .notifications import router as notifications_router
from .admin import router as admin_router
from .jobs import router as jobs_router
from .job_admin import router as job_admin_router


def _cors_origins() -> list[str]:
    configured_origins = os.getenv(
        "API_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173",
    )
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


app = FastAPI(
    title="SchemeSathi AI API",
    description="Independent citizen-facing scheme discovery project API.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(profile_router, prefix="/api/v1")
app.include_router(catalog_router)
app.include_router(eligibility_router)
app.include_router(recommendations_router)
app.include_router(knowledge_router)
app.include_router(assistant_router)
app.include_router(guidance_router)
app.include_router(notifications_router)
app.include_router(admin_router)
app.include_router(jobs_router)
app.include_router(job_admin_router)


@app.get("/health", tags=["health"])
@app.get("/api/v1/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
