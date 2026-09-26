from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import stats_logic
from ..database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/kpis")
def get_kpis(db: Session = Depends(get_db)):
    return stats_logic.kpis(db)


@router.get("/funnel")
def get_funnel(db: Session = Depends(get_db)):
    return stats_logic.funnel(db)


@router.get("/weekly")
def get_weekly(db: Session = Depends(get_db)):
    return stats_logic.candidaturas_por_semana(db)


@router.get("/by-type")
def get_by_type(db: Session = Depends(get_db)):
    return stats_logic.respuestas_por_tipo_y_cv(db)
