"""Migración de un solo uso: PostgreSQL (Docker) -> SQLite de la app.

Uso típico, con el contenedor ``db`` levantado:

    python scripts/migrate_postgres_to_sqlite.py

Otro origen/destino:

    python scripts/migrate_postgres_to_sqlite.py \
        --source postgresql://jobtracker:jobtracker@localhost:5432/jobtracker \
        --target "%LOCALAPPDATA%\\JobTracker\\jobtracker.db"

Qué conserva:
  * IDs originales
  * fechas de hallazgo, candidatura y respuesta
  * max_stage_reached (la razón para usar pg_dump/Postgres y no el CSV)
  * notas, URL y el resto de columnas antiguas

Valida al final:
  * número total de filas
  * conteo por estado
  * distribución de max_stage_reached
  * huella (empresa + puesto + fecha) como multiconjunto
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import psycopg2
import psycopg2.extras
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from app import models  # noqa: E402
from app.database import Base  # noqa: E402
from app.paths import database_path  # noqa: E402

DEFAULT_SOURCE = os.getenv(
    "SOURCE_DATABASE_URL",
    "postgresql://jobtracker:jobtracker@localhost:5432/jobtracker",
)

COLUMNAS = [
    "id",
    "company",
    "position",
    "url",
    "source",
    "found_date",
    "applied_date",
    "location",
    "modality",
    "job_type",
    "cv_version",
    "status",
    "max_stage_reached",
    "last_update",
    "response_date",
    "notes",
]


def _iso(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)


def _fecha_corta(valor) -> str:
    return _iso(valor)[:10]


def huella(fila: dict) -> str:
    """Huella empresa + puesto + fecha (candidatura o hallazgo)."""
    fecha = _fecha_corta(fila.get("applied_date") or fila.get("found_date"))
    texto = "|".join(
        [
            (fila.get("company") or "").strip().casefold(),
            (fila.get("position") or "").strip().casefold(),
            fecha,
        ]
    )
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def leer_postgres(dsn: str) -> list[dict]:
    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SELECT {', '.join(COLUMNAS)} FROM applications ORDER BY id")
            return [dict(fila) for fila in cur.fetchall()]


def leer_sqlite(db: Session) -> list[dict]:
    filas = db.query(models.Application).order_by(models.Application.id).all()
    return [
        {
            "id": fila.id,
            "company": fila.company,
            "position": fila.position,
            "url": fila.url,
            "source": fila.source,
            "found_date": fila.found_date,
            "applied_date": fila.applied_date,
            "location": fila.location,
            "modality": fila.modality,
            "job_type": fila.job_type,
            "cv_version": fila.cv_version,
            "status": fila.status,
            "max_stage_reached": fila.max_stage_reached,
            "last_update": fila.last_update,
            "response_date": fila.response_date,
            "notes": fila.notes,
        }
        for fila in filas
    ]


def resumen(filas: list[dict]) -> dict:
    return {
        "total": len(filas),
        "por_estado": Counter(fila["status"] for fila in filas),
        "por_etapa": Counter(int(fila["max_stage_reached"]) for fila in filas),
        "huellas": Counter(huella(fila) for fila in filas),
        "ids": {int(fila["id"]) for fila in filas},
    }


def comparar(origen: list[dict], destino: list[dict]) -> list[str]:
    a = resumen(origen)
    b = resumen(destino)
    errores: list[str] = []

    if a["total"] != b["total"]:
        errores.append(f"Total distinto: origen={a['total']} destino={b['total']}")
    if a["ids"] != b["ids"]:
        errores.append("Los IDs no coinciden.")
    if a["por_estado"] != b["por_estado"]:
        errores.append(f"Conteo por estado distinto:\n  origen={dict(a['por_estado'])}\n  destino={dict(b['por_estado'])}")
    if a["por_etapa"] != b["por_etapa"]:
        errores.append(f"Distribución de etapa distinta:\n  origen={dict(a['por_etapa'])}\n  destino={dict(b['por_etapa'])}")
    if a["huellas"] != b["huellas"]:
        faltan = a["huellas"] - b["huellas"]
        sobran = b["huellas"] - a["huellas"]
        errores.append(
            f"Huellas distintas: faltan={sum(faltan.values())} sobran={sum(sobran.values())}"
        )

    # Comprobación campo a campo para los datos que el usuario no quiere perder.
    por_id_origen = {int(f["id"]): f for f in origen}
    por_id_destino = {int(f["id"]): f for f in destino}
    for id_ in sorted(a["ids"] & b["ids"]):
        o = por_id_origen[id_]
        d = por_id_destino[id_]
        for campo in ("company", "position", "url", "notes", "max_stage_reached"):
            if (o.get(campo) or "") != (d.get(campo) or ""):
                errores.append(f"ID {id_}: campo {campo} distinto ({o.get(campo)!r} != {d.get(campo)!r})")
        for campo in ("found_date", "applied_date", "response_date"):
            if _fecha_corta(o.get(campo)) != _fecha_corta(d.get(campo)):
                errores.append(
                    f"ID {id_}: campo {campo} distinto "
                    f"({_fecha_corta(o.get(campo))} != {_fecha_corta(d.get(campo))})"
                )
    return errores


def migrar(origen: list[dict], destino_path: Path, overwrite: bool) -> None:
    destino_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{destino_path.as_posix()}"
    engine = create_engine(url)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        existentes = db.query(func.count(models.Application.id)).scalar() or 0
        if existentes and not overwrite:
            raise SystemExit(
                f"El destino ya tiene {existentes} filas: {destino_path}\n"
                "Usa --overwrite si quieres reemplazarlas (haz copia antes)."
            )
        if existentes and overwrite:
            db.query(models.Application).delete()
            db.commit()

        db.bulk_insert_mappings(
            models.Application,
            [
                {
                    "id": fila["id"],
                    "company": fila["company"],
                    "position": fila["position"],
                    "url": fila["url"],
                    "source": fila["source"],
                    "found_date": fila["found_date"],
                    "applied_date": fila["applied_date"],
                    "location": fila["location"],
                    "modality": fila["modality"],
                    "job_type": fila["job_type"],
                    "cv_version": fila["cv_version"],
                    "status": fila["status"],
                    "max_stage_reached": fila["max_stage_reached"],
                    "follow_up_date": None,
                    "last_update": fila["last_update"],
                    "response_date": fila["response_date"],
                    "notes": fila["notes"],
                }
                for fila in origen
            ],
        )
        db.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="DSN de PostgreSQL")
    parser.add_argument(
        "--target",
        default=str(database_path()),
        help="Ruta del fichero SQLite de destino",
    )
    parser.add_argument("--overwrite", action="store_true", help="Vaciar el destino antes de migrar")
    args = parser.parse_args()

    destino_path = Path(args.target).expanduser()
    print(f"Origen : {args.source}")
    print(f"Destino: {destino_path}")

    origen = leer_postgres(args.source)
    print(f"Leídas {len(origen)} filas de PostgreSQL.")
    if not origen:
        print("No hay nada que migrar.")
        return 1

    migrar(origen, destino_path, overwrite=args.overwrite)
    print("Filas insertadas. Validando...")

    engine = create_engine(f"sqlite:///{destino_path.as_posix()}")
    with Session(engine) as db:
        destino = leer_sqlite(db)

    errores = comparar(origen, destino)
    if errores:
        print("\nVALIDACIÓN FALLIDA:")
        for error in errores:
            print(f"  - {error}")
        return 1

    print("\nVALIDACIÓN OK")
    print(f"  Filas: {len(destino)}")
    print(f"  Por estado: {dict(Counter(f['status'] for f in destino))}")
    print(f"  Por etapa:  {dict(sorted(Counter(int(f['max_stage_reached']) for f in destino).items()))}")
    print(f"  Huellas:    {len(set(huella(f) for f in destino))} únicas")
    print("\nDatos migrados. La base original de PostgreSQL sigue intacta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
