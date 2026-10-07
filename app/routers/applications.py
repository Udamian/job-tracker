from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=schemas.ApplicationOut, status_code=201)
def crear(data: schemas.ApplicationCreate, db: Session = Depends(get_db)):
    return crud.create_application(db, data)


@router.get("", response_model=list[schemas.ApplicationOut])
def listar(
    company: Optional[str] = None,
    job_type: Optional[schemas.TipoPuesto] = None,
    modality: Optional[schemas.Modalidad] = None,
    status: Optional[schemas.Estado] = None,
    cv_version: Optional[schemas.VersionCV] = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    return crud.list_applications(
        db,
        company=company,
        job_type=job_type.value if job_type else None,
        modality=modality.value if modality else None,
        status=status.value if status else None,
        cv_version=cv_version.value if cv_version else None,
        skip=skip,
        limit=limit,
    )


@router.get("/export/txt")
def exportar_txt(
    company: Optional[str] = None,
    job_type: Optional[schemas.TipoPuesto] = None,
    modality: Optional[schemas.Modalidad] = None,
    status: Optional[schemas.Estado] = None,
    cv_version: Optional[schemas.VersionCV] = None,
    db: Session = Depends(get_db),
):
    apps = crud.list_applications(
        db,
        company=company,
        job_type=job_type.value if job_type else None,
        modality=modality.value if modality else None,
        status=status.value if status else None,
        cv_version=cv_version.value if cv_version else None,
        skip=0,
        limit=5000,
    )
    lineas = [
        "=" * 80,
        "JOB TRACKER - EXPORTACIÓN DE CANDIDATURAS",
        f"Total de registros: {len(apps)}",
        "=" * 80,
        "",
    ]
    for idx, a in enumerate(apps, start=1):
        lineas.extend([
            f"[{idx}] {a.company.strip()} — {a.position.strip()}",
            "-" * 80,
            f"  ID:                    {a.id}",
            f"  Estado:                {a.status}",
            f"  Fecha encontrada:      {a.found_date}",
            f"  Fecha candidatura:     {a.applied_date or '-'}",
            f"  Fuente:                {a.source}",
            f"  Modalidad:             {a.modality or '-'}",
            f"  Ubicación:             {a.location or '-'}",
            f"  Tipo de puesto:        {a.job_type}",
            f"  Versión de CV:         {a.cv_version or '-'}",
            f"  URL oferta:            {a.url or '-'}",
            f"  Fecha respuesta:       {a.response_date or '-'}",
            f"  Notas:                 {a.notes or '-'}",
            f"  Última actualización:  {a.last_update.strftime('%Y-%m-%d %H:%M:%S') if a.last_update else '-'}",
            "",
        ])
    contenido = "\n".join(lineas)
    return PlainTextResponse(
        content=contenido,
        headers={"Content-Disposition": 'attachment; filename="candidaturas.txt"'},
    )


@router.get("/{application_id}", response_model=schemas.ApplicationOut)
def obtener(application_id: int, db: Session = Depends(get_db)):
    return crud.get_application(db, application_id)


@router.patch("/{application_id}", response_model=schemas.ApplicationOut)
def actualizar(application_id: int, data: schemas.ApplicationUpdate, db: Session = Depends(get_db)):
    return crud.update_application(db, application_id, data)


@router.delete("/{application_id}", status_code=204)
def eliminar(application_id: int, db: Session = Depends(get_db)):
    crud.delete_application(db, application_id)
