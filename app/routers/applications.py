import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse, Response
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
    limit: int = Query(default=500, le=1000),
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


@router.get("/suggestions", response_model=schemas.Suggestions)
def sugerencias(q: str = "", db: Session = Depends(get_db)):
    """Empresas y puestos ya usados, para el autocompletado de la barra."""
    return crud.suggestions(db, q=q)


@router.get("/check", response_model=schemas.DuplicateCheck)
def comprobar_duplicado(
    company: str = Query(min_length=1),
    position: Optional[str] = None,
    exclude_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Avisa si ya hay una candidatura en esa empresa."""
    return crud.check_duplicates(db, company=company, position=position, exclude_id=exclude_id)


@router.get("/attention", response_model=list[schemas.AttentionOut])
def requiere_atencion(db: Session = Depends(get_db)):
    """Candidaturas en espera desde hace más de 21 días."""
    return crud.attention_applications(db)


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
        lineas.extend(
            [
                f"[{idx}] {a.company.strip()} — {a.position.strip()}",
                "-" * 80,
                f"  ID:                    {a.id}",
                f"  Estado:                {a.status}",
                f"  Etapa máxima:          {a.max_stage_reached}",
                f"  Fecha encontrada:      {a.found_date or '-'}",
                f"  Fecha candidatura:     {a.applied_date or '-'}",
                f"  Fuente:                {a.source or '-'}",
                f"  Modalidad:             {a.modality or '-'}",
                f"  Ubicación:             {a.location or '-'}",
                f"  Tipo de puesto:        {a.job_type or '-'}",
                f"  Versión de CV:         {a.cv_version or '-'}",
                f"  URL oferta:            {a.url or '-'}",
                f"  Seguimiento:           {a.follow_up_date or '-'}",
                f"  Fecha respuesta:       {a.response_date or '-'}",
                f"  Notas:                 {a.notes or '-'}",
                f"  Última actualización:  {a.last_update.strftime('%Y-%m-%d %H:%M:%S') if a.last_update else '-'}",
                "",
            ]
        )
    contenido = "\n".join(lineas)
    return PlainTextResponse(
        content=contenido,
        headers={"Content-Disposition": 'attachment; filename="candidaturas.txt"'},
    )


@router.get("/export/csv")
def exportar_csv(
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
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Empresa",
            "Puesto",
            "Estado",
            "Tipo de puesto",
            "CV usado",
            "Fuente",
            "Modalidad",
            "Ubicación",
            "Fecha encontrada",
            "Fecha candidatura",
            "Fecha respuesta",
            "URL",
            "Notas",
            "Última actualización",
            "Etapa máxima",
            "Fecha seguimiento",
        ]
    )
    for a in apps:
        writer.writerow(
            [
                a.id,
                a.company,
                a.position,
                a.status,
                a.job_type or "",
                a.cv_version or "",
                a.source or "",
                a.modality or "",
                a.location or "",
                a.found_date.isoformat() if a.found_date else "",
                a.applied_date.isoformat() if a.applied_date else "",
                a.response_date.isoformat() if a.response_date else "",
                a.url or "",
                a.notes or "",
                a.last_update.strftime("%Y-%m-%d %H:%M:%S") if a.last_update else "",
                a.max_stage_reached,
                a.follow_up_date.isoformat() if a.follow_up_date else "",
            ]
        )
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="candidaturas.csv"'},
    )


@router.post("/restore", response_model=schemas.ApplicationOut, status_code=201)
def restaurar(data: schemas.ApplicationRestore, db: Session = Depends(get_db)):
    """Deshacer un borrado conservando id, fechas y etapa máxima."""
    return crud.restore_application(db, data)


@router.get("/{application_id}", response_model=schemas.ApplicationOut)
def obtener(application_id: int, db: Session = Depends(get_db)):
    return crud.get_application(db, application_id)


@router.patch("/{application_id}", response_model=schemas.ApplicationOut)
def actualizar(
    application_id: int,
    data: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
):
    return crud.update_application(db, application_id, data)


@router.delete("/{application_id}", response_model=schemas.ApplicationOut)
def eliminar(application_id: int, db: Session = Depends(get_db)):
    """Devuelve la candidatura borrada para que el frontend pueda deshacer."""
    return crud.delete_application(db, application_id)
