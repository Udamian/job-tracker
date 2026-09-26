from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Fuente(str, Enum):
    LINKEDIN = "LinkedIn"
    INDEED = "Indeed"
    INFOJOBS = "InfoJobs"
    WEB_EMPRESA = "Web empresa"
    OTRA = "Otra"


class Modalidad(str, Enum):
    REMOTO = "Remoto"
    HIBRIDO = "Híbrido"
    PRESENCIAL = "Presencial"


class TipoPuesto(str, Enum):
    PYTHON = "Python"
    BACKEND = "Backend"
    DATA_ANALYST = "Data Analyst"
    DATA_ENGINEER = "Data Engineer"
    OTRO = "Otro"


class VersionCV(str, Enum):
    BACKEND = "Backend"
    DATA = "Data"
    DATA_ENGINEER = "Data Engineer"
    OTRO = "Otro"


class Estado(str, Enum):
    GUARDADA = "Guardada"
    CANDIDATURA_ENVIADA = "Candidatura enviada"
    CV_VISTO = "CV visto"
    ENTREVISTA = "Entrevista"
    PRUEBA_TECNICA = "Prueba técnica"
    OFERTA = "Oferta"
    RECHAZADA = "Rechazada"
    SIN_RESPUESTA = "Sin respuesta"  # lo asigna el sistema, ver crud.refresh_stale_applications


# El usuario nunca fija "Sin respuesta" a mano: lo calcula el sistema
# a partir de los días transcurridos (ver crud.py).
ESTADOS_EDITABLES_MANUALMENTE = {e for e in Estado if e != Estado.SIN_RESPUESTA}

# Orden del embudo. Rechazada/Sin respuesta son "salidas" del embudo,
# no tienen rango propio: no hacen avanzar max_stage_reached pero
# tampoco lo hacen retroceder.
RANGO_ESTADO = {
    Estado.GUARDADA: 0,
    Estado.CANDIDATURA_ENVIADA: 1,
    Estado.CV_VISTO: 2,
    Estado.ENTREVISTA: 3,
    Estado.PRUEBA_TECNICA: 4,
    Estado.OFERTA: 5,
}


class ApplicationBase(BaseModel):
    company: str
    position: str
    url: Optional[str] = None
    source: Fuente
    found_date: date
    applied_date: Optional[date] = None
    location: Optional[str] = None
    modality: Optional[Modalidad] = None
    job_type: TipoPuesto
    cv_version: Optional[VersionCV] = None
    status: Estado = Estado.GUARDADA
    response_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_no_manual_sin_respuesta(cls, v: Estado) -> Estado:
        if v not in ESTADOS_EDITABLES_MANUALMENTE:
            raise ValueError(
                "El estado 'Sin respuesta' lo asigna el sistema automáticamente "
                "tras 21 días sin novedades; no se puede fijar a mano."
            )
        return v

    @model_validator(mode="after")
    def fechas_y_estado_coherentes(self):
        if self.status != Estado.GUARDADA and self.applied_date is None:
            raise ValueError("Si el estado no es 'Guardada' hace falta indicar 'applied_date'.")
        if self.applied_date and self.applied_date < self.found_date:
            raise ValueError("'applied_date' no puede ser anterior a 'found_date'.")
        if self.response_date and self.applied_date and self.response_date < self.applied_date:
            raise ValueError("'response_date' no puede ser anterior a 'applied_date'.")
        return self


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    """Todos los campos opcionales: es un PATCH parcial.
    La coherencia final se revalida en crud.update_application,
    fusionando esto con el registro existente."""

    company: Optional[str] = None
    position: Optional[str] = None
    url: Optional[str] = None
    source: Optional[Fuente] = None
    found_date: Optional[date] = None
    applied_date: Optional[date] = None
    location: Optional[str] = None
    modality: Optional[Modalidad] = None
    job_type: Optional[TipoPuesto] = None
    cv_version: Optional[VersionCV] = None
    status: Optional[Estado] = None
    response_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_no_manual_sin_respuesta(cls, v: Optional[Estado]) -> Optional[Estado]:
        if v is not None and v not in ESTADOS_EDITABLES_MANUALMENTE:
            raise ValueError("El estado 'Sin respuesta' lo asigna el sistema, no se puede fijar a mano.")
        return v


class ApplicationOut(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    max_stage_reached: int
    last_update: datetime
