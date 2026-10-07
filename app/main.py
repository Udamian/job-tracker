from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from .database import Base, engine
from .routers import applications, stats

# MVP: sin Alembic todavía. Al arrancar, crea las tablas que falten.
# Cuando el modelo de datos se estabilice, merece la pena migrar a
# Alembic para no perder datos al cambiar columnas.
Base.metadata.create_all(bind=engine)

# Migrar automáticamente registros antiguos de cv_version 'Data Engineer' a 'CV General'
try:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE applications SET cv_version = 'CV General' WHERE cv_version = 'Data Engineer'")
        )
except Exception:
    pass

app = FastAPI(title="Job Tracker API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(stats.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("app/static/favicon.ico")


@app.get("/site.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse("app/static/site.webmanifest")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")
