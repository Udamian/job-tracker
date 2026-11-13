from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from .database import Base


class Application(Base):
    """
    Tabla única con cada oferta/candidatura.

    Solo empresa, puesto y estatus son obligatorios. El resto de campos
    antiguos se conservan (no se borra ninguna columna) pero pasan a ser
    opcionales y se editan desde el panel de detalle.

    ``max_stage_reached`` guarda el rango (1-3) más alto alcanzado alguna
    vez. Es lo que permite calcular el embudo sin tabla de historial.

    ``follow_up_date`` es la fecha del último seguimiento manual. El panel
    "Estancados" cuenta 21 días desde aquí (o desde la candidatura si
    nunca se hizo seguimiento).
    """

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(200), nullable=False, index=True)
    position = Column(String(200), nullable=False)
    url = Column(Text, nullable=True)
    source = Column(String(50), nullable=True)
    found_date = Column(Date, nullable=True)
    applied_date = Column(Date, nullable=True)
    location = Column(String(200), nullable=True)
    modality = Column(String(50), nullable=True)
    job_type = Column(String(50), nullable=True, index=True)
    cv_version = Column(String(50), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="Enviada", index=True)
    max_stage_reached = Column(Integer, nullable=False, default=0)
    follow_up_date = Column(Date, nullable=True)
    last_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    response_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
