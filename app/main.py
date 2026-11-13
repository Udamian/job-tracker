from typing import Callable, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from .database import Base, engine, ensure_sqlite_columns
from .paths import resource
from .routers import applications, stats

# MVP: sin Alembic. Al arrancar se crean las tablas que falten y se
# añaden columnas nuevas a bases SQLite antiguas.
Base.metadata.create_all(bind=engine)
ensure_sqlite_columns()

# Normaliza valores heredados de versiones anteriores.
ESTADOS_LEGADOS = {
    "Guardada": "Enviada",
    "Candidatura enviada": "Enviada",
    "Sin respuesta": "Enviada",
    "CV visto": "Contactado",
    "Prueba técnica": "Entrevista",
    "Oferta": "Entrevista",
}

try:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE applications SET cv_version = 'CV General' WHERE cv_version = 'Data Engineer'")
        )
        conn.execute(
            text("UPDATE applications SET cv_version = 'Java Junior' WHERE LOWER(cv_version) = 'java junior'")
        )
        for viejo, nuevo in ESTADOS_LEGADOS.items():
            conn.execute(
                text("UPDATE applications SET status = :nuevo WHERE LOWER(status) = LOWER(:viejo)"),
                {"nuevo": nuevo, "viejo": viejo},
            )
except Exception:
    # En una base recién creada no hay nada que normalizar.
    pass

app = FastAPI(title="Job Tracker API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications.router)
app.include_router(stats.router)

STATIC_DIR = resource("app", "static")
TEMPLATES_DIR = resource("app", "templates")

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# El lanzador de escritorio registra aquí cómo enfocar la ventana nativa.
_focus_handler: Optional[Callable[[], None]] = None


def set_focus_handler(handler: Optional[Callable[[], None]]) -> None:
    global _focus_handler
    _focus_handler = handler


@app.post("/focus", include_in_schema=False)
def focus():
    """Segunda instancia: enfoca la ventana que ya está abierta."""
    if _focus_handler is not None:
        try:
            _focus_handler()
        except Exception:
            pass
    return {"ok": True}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / "favicon.ico")


@app.get("/site.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(STATIC_DIR / "site.webmanifest")


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")
