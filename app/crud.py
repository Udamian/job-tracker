import enum
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from . import models, schemas

DIAS_PARA_SIN_RESPUESTA = 21

# Estados "en juego": si llevan más de N días aquí sin novedades,
# se consideran silencio administrativo (ghosting).
ESTADOS_EN_ESPERA = [schemas.Estado.CANDIDATURA_ENVIADA.value, schemas.Estado.CV_VISTO.value]


def refresh_stale_applications(db: Session) -> int:
    """Pasa a 'Sin respuesta' las candidaturas calladas desde hace >21 días.

    Se llama automáticamente antes de listar candidaturas o calcular
    estadísticas, así el estado siempre sale calculado de los datos
    (fecha de candidatura vs. hoy) y nunca se introduce a mano, tal
    como pide el requisito 2 del documento.
    """
    limite = date.today() - timedelta(days=DIAS_PARA_SIN_RESPUESTA)
    candidatas = (
        db.query(models.Application)
        .filter(models.Application.status.in_(ESTADOS_EN_ESPERA))
        .filter(models.Application.applied_date.isnot(None))
        .filter(models.Application.applied_date <= limite)
        .all()
    )
    for app in candidatas:
        app.status = schemas.Estado.SIN_RESPUESTA.value
    if candidatas:
        db.commit()
    return len(candidatas)


def _rango_de(status_value: str) -> Optional[int]:
    try:
        estado = schemas.Estado(status_value)
    except ValueError:
        return None
    return schemas.RANGO_ESTADO.get(estado)


def _valor(x):
    return x.value if isinstance(x, enum.Enum) else x


def create_application(db: Session, data: schemas.ApplicationCreate) -> models.Application:
    payload = {campo: _valor(getattr(data, campo)) for campo in schemas.ApplicationCreate.model_fields}
    rango = _rango_de(payload["status"]) or 0
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
    refresh_stale_applications(db)
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
        query = query.filter(models.Application.cv_version == cv_version)
    return query.order_by(models.Application.last_update.desc()).offset(skip).limit(limit).all()


def update_application(db: Session, application_id: int, data: schemas.ApplicationUpdate) -> models.Application:
    db_app = get_application(db, application_id)

    merged = {campo: getattr(db_app, campo) for campo in schemas.ApplicationBase.model_fields}
    updates = data.model_dump(exclude_unset=True)
    merged.update(updates)

    try:
        validado = schemas.ApplicationBase(**merged)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())

    for campo in schemas.ApplicationBase.model_fields:
        setattr(db_app, campo, _valor(getattr(validado, campo)))

    nuevo_rango = _rango_de(db_app.status)
    if nuevo_rango is not None:
        db_app.max_stage_reached = max(db_app.max_stage_reached, nuevo_rango)

    db.commit()
    db.refresh(db_app)
    return db_app


def delete_application(db: Session, application_id: int) -> None:
    db_app = get_application(db, application_id)
    db.delete(db_app)
    db.commit()
