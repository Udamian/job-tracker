import unicodedata
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios colapsados. Para comparar."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return " ".join(sin_tildes.strip().lower().split())


class _EnumNormalizado(str, Enum):
    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            buscado = normalizar(value)
            for miembro in cls:
                if normalizar(miembro.value) == buscado:
                    return miembro
        return None


class Fuente(_EnumNormalizado):
    LINKEDIN = "LinkedIn"
    INDEED = "Indeed"
    INFOJOBS = "InfoJobs"
    WEB_EMPRESA = "Web empresa"
    OTRA = "Otra"


class Modalidad(_EnumNormalizado):
    REMOTO = "Remoto"
    HIBRIDO = "Híbrido"
    PRESENCIAL = "Presencial"


class TipoPuesto(_EnumNormalizado):
    PYTHON = "Python"
    BACKEND = "Backend"
    DATA_ANALYST = "Data Analyst"
    DATA_ENGINEER = "Data Engineer"
    OTRO = "Otro"


class VersionCV(_EnumNormalizado):
    BACKEND = "Backend"
    DATA = "Data"
    CV_GENERAL = "CV General"
    JAVA_JUNIOR = "Java Junior"
    OTRO = "Otro"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            val_clean = normalizar(value)
            if val_clean in ("data engineer", "data_engineer"):
                return cls.CV_GENERAL
            if val_clean in ("cv general", "cv_general", "general"):
                return cls.CV_GENERAL
            if val_clean in ("java junior", "java_junior", "javajunior", "java jr", "java_jr"):
                return cls.JAVA_JUNIOR
        return super()._missing_(value)


class Estado(_EnumNormalizado):
    """Los cuatro estados del tablero.

    Los valores antiguos (Guardada, Candidatura enviada, CV visto,
    Prueba técnica, Oferta, Sin respuesta) se siguen aceptando y se
    normalizan a uno de estos cuatro. "Sin respuesta" ya no es un estado:
    esas candidaturas quedan en Enviada y aparecen en el panel de
    Estancados cuando pasan 21 días sin novedades.
    """

    ENVIADA = "Enviada"
    CONTACTADO = "Contactado"
    ENTREVISTA = "Entrevista"
    RECHAZADA = "Rechazada"

    @classmethod
    def _missing_(cls, value):
        encontrado = super()._missing_(value)
        if encontrado is not None:
            return encontrado
        if isinstance(value, str):
            alias = {
                # Valores nuevos y sinónimos.
                "enviado": cls.ENVIADA,
                "aplicada": cls.ENVIADA,
                "aplicado": cls.ENVIADA,
                "contacto": cls.CONTACTADO,
                "contactada": cls.CONTACTADO,
                "rechazo": cls.RECHAZADA,
                "rechazado": cls.RECHAZADA,
                # Valores heredados de la versión anterior.
                "guardada": cls.ENVIADA,
                "candidatura enviada": cls.ENVIADA,
                "cv visto": cls.CONTACTADO,
                "cv": cls.CONTACTADO,
                "cv-visto": cls.CONTACTADO,
                "prueba": cls.ENTREVISTA,
                "prueba tecnica": cls.ENTREVISTA,
                "tecnica": cls.ENTREVISTA,
                "oferta": cls.ENTREVISTA,
                "sin respuesta": cls.ENVIADA,
                "sin-respuesta": cls.ENVIADA,
                "ghosting": cls.ENVIADA,
                "ghosted": cls.ENVIADA,
            }
            return alias.get(normalizar(value))
        return None


# Todos los estados se pueden fijar a mano. El antiguo "Sin respuesta"
# automático se sustituye por el panel "Estancados", que propone la
# acción y deja decidir al usuario.
ESTADOS_EDITABLES_MANUALMENTE = set(Estado)

# Orden del embudo. Rechazada es una salida: no hace avanzar
# max_stage_reached pero tampoco lo hace retroceder.
RANGO_ESTADO = {
    Estado.ENVIADA: 1,
    Estado.CONTACTADO: 2,
    Estado.ENTREVISTA: 3,
}


class ApplicationBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    company: str = Field(min_length=1, max_length=200)
    position: str = Field(min_length=1, max_length=200)
    url: Optional[str] = None
    source: Optional[Fuente] = None
    found_date: Optional[date] = None
    applied_date: Optional[date] = None
    location: Optional[str] = None
    modality: Optional[Modalidad] = None
    job_type: Optional[TipoPuesto] = None
    cv_version: Optional[VersionCV] = None
    status: Estado = Estado.ENVIADA
    follow_up_date: Optional[date] = None
    response_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("url", "location", "notes", mode="before")
    @classmethod
    def sanitizar_textos_opcionales(cls, v):
        if isinstance(v, str):
            limpio = v.strip()
            return limpio or None
        return v

    @field_validator("source", "modality", "job_type", "cv_version", mode="before")
    @classmethod
    def cadena_vacia_a_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @model_validator(mode="after")
    def fechas_coherentes(self):
        # Fecha automática: si no se indica nada, hoy.
        if self.found_date is None:
            self.found_date = self.applied_date or date.today()

        # Captura rápida: toda candidatura nueva cuenta como enviada; la
        # fecha de candidatura se rellena sola.
        if self.applied_date is None:
            self.applied_date = self.found_date

        # Registro retroactivo ("ayer"): no tiene sentido que la fecha de
        # candidatura sea anterior a la de hallazgo; la ajustamos.
        if self.found_date and self.applied_date and self.applied_date < self.found_date:
            self.found_date = self.applied_date

        if self.response_date and self.applied_date and self.response_date < self.applied_date:
            raise ValueError("'response_date' no puede ser anterior a 'applied_date'.")
        return self


class ApplicationCreate(ApplicationBase):
    """Todo opcional salvo empresa, puesto y estatus (con default)."""


class ApplicationUpdate(BaseModel):
    """PATCH parcial: cualquier campo puede venir o no."""

    model_config = ConfigDict(str_strip_whitespace=True)

    company: Optional[str] = Field(default=None, min_length=1, max_length=200)
    position: Optional[str] = Field(default=None, min_length=1, max_length=200)
    url: Optional[str] = None
    source: Optional[Fuente] = None
    found_date: Optional[date] = None
    applied_date: Optional[date] = None
    location: Optional[str] = None
    modality: Optional[Modalidad] = None
    job_type: Optional[TipoPuesto] = None
    cv_version: Optional[VersionCV] = None
    status: Optional[Estado] = None
    follow_up_date: Optional[date] = None
    response_date: Optional[date] = None
    notes: Optional[str] = None

    @field_validator("url", "location", "notes", mode="before")
    @classmethod
    def sanitizar_textos_opcionales(cls, v):
        if isinstance(v, str):
            limpio = v.strip()
            return limpio or None
        return v

    @field_validator("source", "modality", "job_type", "cv_version", mode="before")
    @classmethod
    def cadena_vacia_a_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v


class ApplicationOut(ApplicationBase):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    id: int
    max_stage_reached: int
    last_update: datetime


class ApplicationRestore(ApplicationBase):
    """Payload que devuelve DELETE y que permite deshacer el borrado."""

    id: Optional[int] = None
    max_stage_reached: Optional[int] = None


class AttentionOut(ApplicationOut):
    days_waiting: int


class DuplicateMatch(BaseModel):
    id: int
    company: str
    position: str
    status: str
    applied_date: Optional[date] = None
    days_ago: int


class DuplicateCheck(BaseModel):
    duplicate: bool
    message: Optional[str] = None
    matches: list[DuplicateMatch] = Field(default_factory=list)


class Suggestions(BaseModel):
    companies: list[str] = Field(default_factory=list)
    positions: list[str] = Field(default_factory=list)
