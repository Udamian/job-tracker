from typing import Optional

from fastapi import APIRouter, Depends, Query
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


@router.get("/{application_id}", response_model=schemas.ApplicationOut)
def obtener(application_id: int, db: Session = Depends(get_db)):
    return crud.get_application(db, application_id)


@router.patch("/{application_id}", response_model=schemas.ApplicationOut)
def actualizar(application_id: int, data: schemas.ApplicationUpdate, db: Session = Depends(get_db)):
    return crud.update_application(db, application_id, data)


@router.delete("/{application_id}", status_code=204)
def eliminar(application_id: int, db: Session = Depends(get_db)):
    crud.delete_application(db, application_id)
