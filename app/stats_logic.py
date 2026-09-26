from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from . import models, schemas
from .crud import refresh_stale_applications

RANGO = schemas.RANGO_ESTADO

COLUMNAS = ["id", "job_type", "cv_version", "status", "max_stage_reached", "found_date", "applied_date"]


def _dataframe(db: Session) -> pd.DataFrame:
    """Vuelca la tabla applications a un DataFrame. Al ser un tracker
    personal (cientos de filas, no millones), traer todo a pandas y
    agregar en memoria es más simple que hacerlo en SQL, y es el mundo
    en el que te vas a mover más cómodo."""
    refresh_stale_applications(db)
    rows = db.query(models.Application).all()
    data = [{c: getattr(r, c) for c in COLUMNAS} for r in rows]
    return pd.DataFrame(data, columns=COLUMNAS)


def _es_candidatura(df: pd.DataFrame) -> pd.Series:
    return df["max_stage_reached"] >= RANGO[schemas.Estado.CANDIDATURA_ENVIADA]


def _es_respuesta(df: pd.DataFrame) -> pd.Series:
    """Una respuesta = llegó al menos a 'CV visto', o directamente la
    rechazaron sin más trámite (un "no" también es una respuesta)."""
    return (df["max_stage_reached"] >= RANGO[schemas.Estado.CV_VISTO]) | (
        df["status"] == schemas.Estado.RECHAZADA.value
    )


def kpis(db: Session) -> dict:
    df = _dataframe(db)
    vacio = {
        "candidaturas_totales": 0,
        "esta_semana": 0,
        "respuestas": 0,
        "entrevistas": 0,
        "pruebas_tecnicas": 0,
        "ofertas": 0,
        "tasa_respuesta": 0.0,
        "tasa_entrevista": 0.0,
    }
    if df.empty:
        return vacio

    candidatas = df[_es_candidatura(df)]
    total = len(candidatas)
    if total == 0:
        return vacio

    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    esta_semana = candidatas[candidatas["applied_date"].apply(lambda d: d is not None and d >= inicio_semana)]

    respuestas = candidatas[_es_respuesta(candidatas)]
    entrevistas = candidatas[candidatas["max_stage_reached"] >= RANGO[schemas.Estado.ENTREVISTA]]
    pruebas = candidatas[candidatas["max_stage_reached"] >= RANGO[schemas.Estado.PRUEBA_TECNICA]]
    ofertas = candidatas[candidatas["max_stage_reached"] >= RANGO[schemas.Estado.OFERTA]]

    return {
        "candidaturas_totales": total,
        "esta_semana": len(esta_semana),
        "respuestas": len(respuestas),
        "entrevistas": len(entrevistas),
        "pruebas_tecnicas": len(pruebas),
        "ofertas": len(ofertas),
        "tasa_respuesta": round(len(respuestas) / total * 100, 1),
        "tasa_entrevista": round(len(entrevistas) / total * 100, 1),
    }


def funnel(db: Session) -> list[dict]:
    df = _dataframe(db)
    etapas = [
        ("Ofertas guardadas", 0),
        ("Candidaturas enviadas", RANGO[schemas.Estado.CANDIDATURA_ENVIADA]),
        ("Respuestas (CV visto o más)", RANGO[schemas.Estado.CV_VISTO]),
        ("Entrevistas", RANGO[schemas.Estado.ENTREVISTA]),
        ("Pruebas técnicas", RANGO[schemas.Estado.PRUEBA_TECNICA]),
        ("Ofertas recibidas", RANGO[schemas.Estado.OFERTA]),
    ]
    if df.empty:
        return [{"etapa": nombre, "cantidad": 0} for nombre, _ in etapas]
    return [
        {"etapa": nombre, "cantidad": int((df["max_stage_reached"] >= rango).sum())} for nombre, rango in etapas
    ]


def candidaturas_por_semana(db: Session) -> list[dict]:
    df = _dataframe(db)
    con_fecha = df[df["applied_date"].notna()].copy()
    if con_fecha.empty:
        return []
    con_fecha["applied_date"] = pd.to_datetime(con_fecha["applied_date"])
    con_fecha["semana"] = con_fecha["applied_date"].dt.to_period("W").apply(lambda p: p.start_time.date().isoformat())
    agrupado = con_fecha.groupby("semana").size().reset_index(name="candidaturas")
    return agrupado.sort_values("semana").to_dict(orient="records")


def respuestas_por_tipo_y_cv(db: Session) -> list[dict]:
    df = _dataframe(db)
    candidatas = df[_es_candidatura(df)].copy()
    if candidatas.empty:
        return []
    candidatas["respuesta"] = _es_respuesta(candidatas)
    agrupado = (
        candidatas.groupby(["job_type", "cv_version"], dropna=False)
        .agg(candidaturas=("id", "count"), respuestas=("respuesta", "sum"))
        .reset_index()
    )
    agrupado["tasa_respuesta"] = (agrupado["respuestas"] / agrupado["candidaturas"] * 100).round(1)
    agrupado["cv_version"] = agrupado["cv_version"].fillna("Sin especificar")
    return agrupado.to_dict(orient="records")
