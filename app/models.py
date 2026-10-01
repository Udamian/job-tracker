from sqlalchemy import Column, DateTime, Date, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class Application(Base):
    """
    Tabla única (a propósito, ver sección 5 del diseño) con cada
    oferta/candidatura.

    `max_stage_reached` es la pieza clave para poder calcular el embudo
    (KPIs y gráfico "funnel") SIN necesitar una tabla de historial:
    guarda el rango (0-5) más alto que la candidatura ha alcanzado
    alguna vez, aunque después la rechacen o se quede sin respuesta.
    Ver `schemas.RANGO_ESTADO` para el mapeo estado -> rango.
    """

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(200), nullable=False, index=True)
    position = Column(String(200), nullable=False)
    url = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)
    found_date = Column(Date, nullable=False)
    applied_date = Column(Date, nullable=True)
    location = Column(String(200), nullable=True)
    modality = Column(String(50), nullable=True)
    job_type = Column(String(50), nullable=False, index=True)
    cv_version = Column(String(50), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="Guardada", index=True)
    max_stage_reached = Column(Integer, nullable=False, default=0)
    last_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    response_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
