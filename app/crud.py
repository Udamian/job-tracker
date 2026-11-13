import enum
from collections import Counter
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import inference, models, schemas

DIAS_ESTANCADO = 21

# Estados "en juego": si llevan más de N días aquí sin novedades,
# aparecen en "Estancados" (ya no se cambian solos).
ESTADOS_EN_ESPERA = [
    schemas.Estado.ENVIADA.value,
    schemas.Estado.CONTACTADO.value,
]


def _rango_de(status_value: str) -> Optional[int]:
    try:
        estado = schemas.Estado(status_value)
    except ValueError:
        return None
    return schemas.RANGO_ESTADO.get(estado)


def _valor(x):
    return x.value if isinstance(x, enum.Enum) else x


def _inferir_job_type(payload: dict) -> str:
    if payload.get("job_type"):
        return _valor(payload["job_type"])
    return inference.inferir_tipo_puesto(payload.get("position"), payload.get("notes"))


def create_application(db: Session, data: schemas.ApplicationCreate) -> models.Application:
    payload = {
        campo: _valor(getattr(data, campo)) for campo in schemas.ApplicationCreate.model_fields
    }
    payload["job_type"] = _inferir_job_type(payload)
    rango = _rango_de(payload["status"])
    if rango is None:  # Rechazada: al menos consta como enviada.
        rango = schemas.RANGO_ESTADO[schemas.Estado.ENVIADA]

    db_app = models.Application(**payload, max_stage_reached=rango)
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


def get_application(db: Session, application_id: int) -> models.Application:
    app = db.get(models.Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Candidatura no encontrada")
    return app


def list_applications(
    db: Session,
    company: Optional[str] = None,
    job_type: Optional[str] = None,
    modality: Optional[str] = None,
    status: Optional[str] = None,
    cv_version: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = db.query(models.Application)
    if company:
        query = query.filter(models.Application.company.ilike(f"%{company}%"))
    if job_type:
        query = query.filter(models.Application.job_type == job_type)
    if modality:
        query = query.filter(models.Application.modality == modality)
    if status:
        query = query.filter(models.Application.status == status)
    if cv_version:
        if cv_version == schemas.VersionCV.CV_GENERAL.value:
            query = query.filter(models.Application.cv_version.in_(["CV General", "Data Engineer"]))
        elif cv_version == schemas.VersionCV.JAVA_JUNIOR.value:
            query = query.filter(models.Application.cv_version.in_(["Java Junior", "Java junior"]))
        else:
            query = query.filter(models.Application.cv_version == cv_version)
    return query.order_by(models.Application.last_update.desc()).offset(skip).limit(limit).all()


def update_application(
    db: Session, application_id: int, data: schemas.ApplicationUpdate
) -> models.Application:
    db_app = get_application(db, application_id)

    merged = {
        campo: _valor(getattr(db_app, campo))
        for campo in schemas.ApplicationBase.model_fields
    }
    updates = data.model_dump(exclude_unset=True)
    merged.update(updates)

    if not merged.get("applied_date"):
        merged["applied_date"] = merged.get("found_date") or date.today()
    if merged.get("found_date") is None:
        merged["found_date"] = merged.get("applied_date") or date.today()
    if not merged.get("job_type"):
        merged["job_type"] = inference.inferir_tipo_puesto(
            merged.get("position"), merged.get("notes")
        )

    try:
        validado = schemas.ApplicationBase(**merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    for campo in schemas.ApplicationBase.model_fields:
        setattr(db_app, campo, _valor(getattr(validado, campo)))

    nuevo_rango = _rango_de(db_app.status)
    if nuevo_rango is not None:
        db_app.max_stage_reached = max(db_app.max_stage_reached or 0, nuevo_rango)

    db.commit()
    db.refresh(db_app)
    return db_app


def delete_application(db: Session, application_id: int) -> schemas.ApplicationOut:
    db_app = get_application(db, application_id)
    snapshot = schemas.ApplicationOut.model_validate(db_app)
    db.delete(db_app)
    db.commit()
    return snapshot


def restore_application(db: Session, data: schemas.ApplicationRestore) -> models.Application:
    """Reinserta una candidatura borrada conservando id y etapa máxima."""
    payload = {
        campo: _valor(getattr(data, campo)) for campo in schemas.ApplicationBase.model_fields
    }
    payload["job_type"] = _inferir_job_type(payload)
    rango = _rango_de(payload["status"])
    payload["max_stage_reached"] = (
        data.max_stage_reached
        if data.max_stage_reached is not None
        else (rango if rango is not None else schemas.RANGO_ESTADO[schemas.Estado.ENVIADA])
    )

    if data.id is not None and db.get(models.Application, data.id) is None:
        payload["id"] = data.id

    db_app = models.Application(**payload)
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


def attention_applications(db: Session) -> list[schemas.AttentionOut]:
    """Candidaturas en espera con más de 21 días desde el último movimiento.

    No cambia nada: devuelve la lista para el panel "Estancados" y deja
    que el usuario decida si hace seguimiento o la rechaza con un clic.
    """
    hoy = date.today()
    apps = (
        db.query(models.Application)
        .filter(models.Application.status.in_(ESTADOS_EN_ESPERA))
        .all()
    )
    resultado: list[schemas.AttentionOut] = []
    for app in apps:
        referencia = app.follow_up_date or app.applied_date or app.found_date
        if not referencia:
            continue
        dias = (hoy - referencia).days
        if dias < DIAS_ESTANCADO:
            continue
        base = schemas.ApplicationOut.model_validate(app)
        salida = schemas.AttentionOut(**base.model_dump(), days_waiting=dias)
        resultado.append(salida)
    return sorted(resultado, key=lambda a: a.days_waiting, reverse=True)


def suggestions(db: Session, q: str = "") -> schemas.Suggestions:
    filas = db.query(models.Application.company, models.Application.position).all()
    empresas = Counter(fila[0].strip() for fila in filas if fila[0] and fila[0].strip())
    puestos = Counter(fila[1].strip() for fila in filas if fila[1] and fila[1].strip())

    buscado = schemas.normalizar(q) if q else ""

    def filtrar(contador: Counter) -> list[str]:
        elementos = [
            (nombre, veces)
            for nombre, veces in contador.items()
            if not buscado or buscado in schemas.normalizar(nombre)
        ]
        elementos.sort(key=lambda par: (-par[1], par[0].casefold()))
        return [nombre for nombre, _ in elementos[:8]]

    return schemas.Suggestions(companies=filtrar(empresas), positions=filtrar(puestos))


def check_duplicates(
    db: Session,
    company: str,
    position: Optional[str] = None,
    exclude_id: Optional[int] = None,
) -> schemas.DuplicateCheck:
    objetivo = schemas.normalizar(company)
    if not objetivo:
        return schemas.DuplicateCheck(duplicate=False)

    hoy = date.today()
    coincidencias: list[schemas.DuplicateMatch] = []
    for app in db.query(models.Application).all():
        if exclude_id is not None and app.id == exclude_id:
            continue
        if schemas.normalizar(app.company) != objetivo:
            continue
        referencia = app.applied_date or app.found_date
        if referencia is None and app.last_update is not None:
            referencia = app.last_update.date()
        dias = (hoy - referencia).days if referencia else 0
        coincidencias.append(
            schemas.DuplicateMatch(
                id=app.id,
                company=app.company,
                position=app.position,
                status=app.status,
                applied_date=app.applied_date,
                days_ago=max(dias, 0),
            )
        )

    if not coincidencias:
        return schemas.DuplicateCheck(duplicate=False)

    coincidencias.sort(key=lambda m: m.days_ago)
    reciente = coincidencias[0]
    cuando = "Hoy" if reciente.days_ago == 0 else f"Hace {reciente.days_ago} días"
    if position and any(
        schemas.normalizar(m.position) == schemas.normalizar(position) for m in coincidencias
    ):
        mensaje = f"{cuando} ya aplicaste a {company} · {position}."
    else:
        mensaje = (
            f"{cuando} ya aplicaste a {company} "
            f"({reciente.position}, {reciente.status})."
        )
    return schemas.DuplicateCheck(
        duplicate=True,
        message=mensaje,
        matches=coincidencias[:5],
    )
