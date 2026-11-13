import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from .paths import database_path


def _database_url() -> str:
    """SQLite en la carpeta de datos del usuario por defecto.

    ``DATABASE_URL`` sigue existiendo para tests, para el script de
    migración y para quien quiera apuntar a otra base puntualmente.
    """
    return os.getenv("DATABASE_URL") or f"sqlite:///{database_path().as_posix()}"


DATABASE_URL = _database_url()

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_sqlite_columns() -> None:
    """Añade columnas nuevas a bases SQLite creadas con versiones antiguas.

    ``create_all`` no altera tablas existentes. Para columnas nullable
    basta un ``ALTER TABLE ... ADD COLUMN``.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        existe = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='applications'")
        ).first()
        if not existe:
            return
        columnas = {row[1] for row in conn.execute(text("PRAGMA table_info(applications)"))}
        if "follow_up_date" not in columnas:
            conn.execute(text("ALTER TABLE applications ADD COLUMN follow_up_date DATE"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
