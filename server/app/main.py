from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.api.v1 import environments, ai_providers, analyses, recommendations, reports

app = FastAPI(title="Observia - Dynatrace AI Analysis Platform", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(environments.router, prefix="/api/v1/environments", tags=["environments"])
app.include_router(ai_providers.router, prefix="/api/v1/ai-providers", tags=["ai-providers"])
app.include_router(analyses.router, prefix="/api/v1/analyses", tags=["analyses"])
app.include_router(recommendations.router, prefix="/api/v1/recommendations", tags=["recommendations"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])

# Import metrics from reports module
from app.api.v1.reports import metrics


@app.on_event("startup")
async def startup():
    from app.db.database import init_db
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    checks: dict[str, str] = {}
    try:
        from app.db.database import engine
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    overall = "ready" if all(v == "ok" for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ready" else 503
    return JSONResponse(content={"status": overall, **checks}, status_code=status_code)


@app.get("/metrics")
async def get_metrics():
    """Get Prometheus metrics in text format."""
    from app.api.v1.reports import metrics
    lines = [
        "# HELP observia_analysis_total Total number of analyses requested",
        "# TYPE observia_analysis_total counter",
        f"observia_analysis_total {metrics.analysis_total}",
        "",
        "# HELP observia_analysis_completed Total number of completed analyses",
        "# TYPE observia_analysis_completed counter",
        f"observia_analysis_completed {metrics.analysis_completed}",
        "",
        "# HELP observia_analysis_failed Total number of failed analyses",
        "# TYPE observia_analysis_failed counter",
        f"observia_analysis_failed {metrics.analysis_failed}",
        "",
        "# HELP observia_reports_generated Total number of reports generated",
        "# TYPE observia_reports_generated counter",
        f"observia_reports_generated {metrics.reports_generated}",
    ]
    return "\n".join(lines)
