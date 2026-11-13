"""Deducción del tipo de puesto a partir del texto de la oferta.

La captura rápida ya no pregunta "tipo de puesto". Para que el gráfico
"Eficacia por perfil y CV" siga funcionando, se infiere con reglas
sencillas y predecibles. Nunca es obligatorio: si no hay coincidencia,
queda como "Otro".
"""

from .schemas import TipoPuesto

# El orden importa: las reglas más específicas van primero.
REGLAS = [
    (
        TipoPuesto.DATA_ENGINEER,
        (
            "data engineer",
            "ingeniero de datos",
            "ingeniera de datos",
            "pyspark",
            "databricks",
            "spark",
            "big data",
            "etl",
            "airflow",
            "kafka",
            "dbt",
        ),
    ),
    (
        TipoPuesto.DATA_ANALYST,
        (
            "data analyst",
            "analista de datos",
            "analista datos",
            "business intelligence",
            "power bi",
            "tableau",
            "looker",
            "microstrategy",
            "qlik",
        ),
    ),
    (
        TipoPuesto.PYTHON,
        (
            "python",
            "django",
            "flask",
            "fastapi",
            "pandas",
            "numpy",
        ),
    ),
    (
        TipoPuesto.BACKEND,
        (
            "backend",
            "back-end",
            "back end",
            "java",
            "spring",
            "microservicio",
            "microservice",
            "node",
            "api rest",
            "programador",
            "developer",
            "desarrollador",
        ),
    ),
]


def inferir_tipo_puesto(*textos: str | None) -> str:
    """Devuelve el valor de ``TipoPuesto`` que mejor encaja con el texto."""
    contenido = " ".join(t for t in textos if t).lower()
    if not contenido.strip():
        return TipoPuesto.OTRO.value
    for tipo, agujas in REGLAS:
        if any(aguja in contenido for aguja in agujas):
            return tipo.value
    return TipoPuesto.OTRO.value
