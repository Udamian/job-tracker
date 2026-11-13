from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

from . import models, schemas

RANGO = schemas.RANGO_ESTADO

COLUMNAS = [
    "id",
    "job_type",
    "cv_version",
    "status",
    "max_stage_reached",
    "found_date",
    "applied_date",
]


def _dataframe(db: Session) -> pd.DataFrame:
    """Vuelca la tabla a un DataFrame. Son cientos de filas: agregar en
    memoria es más simple y legible que hacerlo en SQL."""
    rows = db.query(models.Application).all()
    data = [{c: getattr(r, c) for c in COLUMNAS} for r in rows]
    df = pd.DataFrame(data, columns=COLUMNAS)
    if not df.empty:
        df["cv_version"] = df["cv_version"].replace(
            {
                "Data Engineer": "CV General",
                "Java junior": "Java Junior",
            }
        )
    return df


def _es_candidatura(df: pd.DataFrame) -> pd.Series:
    return df["max_stage_reached"] >= RANGO[schemas.Estado.ENVIADA]


def _es_respuesta(df: pd.DataFrame) -> pd.Series:
    """Una respuesta = llegó al menos a 'Contactado', o la rechazaron
    directamente (un "no" también es una respuesta)."""
    return (df["max_stage_reached"] >= RANGO[schemas.Estado.CONTACTADO]) | (
        df["status"] == schemas.Estado.RECHAZADA.value
    )


def kpis(db: Session) -> dict:
    df = _dataframe(db)
    vacio = {
        "candidaturas_totales": 0,
        "hoy": 0,
        "esta_semana": 0,
        "respuestas": 0,
        "contactadas": 0,
        "entrevistas": 0,
        "rechazadas": 0,
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
    aplicadas_hoy = candidatas[
        candidatas["applied_date"].apply(lambda d: d is not None and d == hoy)
    ]
    esta_semana = candidatas[
        candidatas["applied_date"].apply(lambda d: d is not None and inicio_semana <= d <= hoy)
    ]

    respuestas = candidatas[_es_respuesta(candidatas)]
    contactadas = candidatas[
        candidatas["max_stage_reached"] >= RANGO[schemas.Estado.CONTACTADO]
    ]
    entrevistas = candidatas[
        candidatas["max_stage_reached"] >= RANGO[schemas.Estado.ENTREVISTA]
    ]
    rechazadas = candidatas[candidatas["status"] == schemas.Estado.RECHAZADA.value]

    return {
        "candidaturas_totales": total,
        "hoy": len(aplicadas_hoy),
        "esta_semana": len(esta_semana),
        "respuestas": len(respuestas),
        "contactadas": len(contactadas),
        "entrevistas": len(entrevistas),
        "rechazadas": len(rechazadas),
        "tasa_respuesta": round(len(respuestas) / total * 100, 1),
        "tasa_entrevista": round(len(entrevistas) / total * 100, 1),
    }


def funnel(db: Session) -> list[dict]:
    df = _dataframe(db)
    etapas = [
        ("Enviadas", RANGO[schemas.Estado.ENVIADA]),
        ("Contactadas", RANGO[schemas.Estado.CONTACTADO]),
        ("Entrevistas", RANGO[schemas.Estado.ENTREVISTA]),
    ]
    if df.empty:
        resultado = [{"etapa": nombre, "cantidad": 0} for nombre, _ in etapas]
        resultado.append({"etapa": "Rechazadas", "cantidad": 0})
        return resultado

    resultado = [
        {"etapa": nombre, "cantidad": int((df["max_stage_reached"] >= rango).sum())}
        for nombre, rango in etapas
    ]
    resultado.append(
        {
            "etapa": "Rechazadas",
            "cantidad": int((df["status"] == schemas.Estado.RECHAZADA.value).sum()),
        }
    )
    return resultado


def candidaturas_por_semana(db: Session) -> list[dict]:
    df = _dataframe(db)
    con_fecha = df[df["applied_date"].notna()].copy()
    if con_fecha.empty:
        return []
    con_fecha["applied_date"] = pd.to_datetime(con_fecha["applied_date"])
    con_fecha["semana"] = con_fecha["applied_date"].dt.to_period("W").apply(
        lambda p: p.start_time.date().isoformat()
    )
    agrupado = con_fecha.groupby("semana").size().reset_index(name="candidaturas")
    return agrupado.sort_values("semana").to_dict(orient="records")


def respuestas_por_tipo_y_cv(db: Session) -> list[dict]:
    df = _dataframe(db)
    candidatas = df[_es_candidatura(df)].copy()
    if candidatas.empty:
        return []
    candidatas["job_type"] = candidatas["job_type"].fillna("Sin especificar")
    candidatas["cv_version"] = candidatas["cv_version"].fillna("Sin especificar")
    candidatas["respuesta"] = _es_respuesta(candidatas)
    agrupado = (
        candidatas.groupby(["job_type", "cv_version"], dropna=False)
        .agg(candidaturas=("id", "count"), respuestas=("respuesta", "sum"))
        .reset_index()
    )
    agrupado["tasa_respuesta"] = (
        agrupado["respuestas"] / agrupado["candidaturas"] * 100
    ).round(1)
    return agrupado.to_dict(orient="records")
