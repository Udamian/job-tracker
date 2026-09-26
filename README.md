# Job Tracker — V2

Tracker personal de búsqueda de empleo. Backend en FastAPI + PostgreSQL,
estadísticas calculadas con Pandas, dashboard en HTML/JS puro (sin frameworks
de frontend, tal como pedía el diseño original).

## Stack

Python · FastAPI · PostgreSQL · SQLAlchemy · Pydantic · Pandas · Docker · pytest

## Cómo arrancarlo

```bash
docker compose up --build
```

- API + docs interactivas: http://localhost:8000/docs
- Dashboard: http://localhost:8000/dashboard

Las tablas se crean solas al arrancar (no hace falta migrar nada a mano en el MVP).

### Sin Docker (desarrollo rápido)

Si no quieres levantar Postgres todavía, la app funciona igual con SQLite
(fichero local `jobtracker.db`), que es el valor por defecto si no defines
`DATABASE_URL`:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

Los tests usan una base de datos SQLite en memoria (no necesitan Postgres
levantado), así que corren rápido y no dependen de Docker.

## Endpoints principales

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/applications` | Crear candidatura |
| GET | `/applications` | Listar (filtros: `company`, `job_type`, `modality`, `status`, `cv_version`) |
| GET | `/applications/{id}` | Ver una candidatura |
| PATCH | `/applications/{id}` | Editar / cambiar estado |
| DELETE | `/applications/{id}` | Borrar |
| GET | `/stats/kpis` | Totales, respuestas, entrevistas, tasas... |
| GET | `/stats/funnel` | Embudo completo |
| GET | `/stats/weekly` | Candidaturas por semana (para el gráfico) |
| GET | `/stats/by-type` | Tasa de respuesta por tipo de puesto / CV |

## Decisiones de diseño que quizá no son obvias

**1. `max_stage_reached` en vez de una tabla de historial.**
El documento original habla de un embudo tipo "100 guardadas → 60
candidaturas → 12 respuestas → ...", es decir, un embudo *acumulado*: cuenta
cuántas candidaturas llegaron *alguna vez* a cada etapa, no en cuál están
ahora. Para calcular eso sin montar una tabla `status_history` (que el propio
documento deja para más adelante), cada candidatura guarda el rango más alto
que ha alcanzado (0=Guardada … 5=Oferta). Si luego la rechazan, ese número no
baja. Es un atajo deliberado: menos tablas, mismo resultado, y migrar a una
tabla de historial completa el día de mañana es sencillo porque no rompe el
modelo actual.

**2. "Sin respuesta" nunca se fija a mano.**
La API rechaza (`422`) cualquier intento de crear o editar una candidatura
con `status: "Sin respuesta"` directamente. Ese estado lo asigna el propio
sistema: cada vez que listas candidaturas o pides estadísticas, se ejecuta
`refresh_stale_applications()`, que busca candidaturas en "Candidatura
enviada" o "CV visto" con `applied_date` de hace más de 21 días y las pasa a
"Sin respuesta". Está pensado como comprobación al vuelo (MVP); si el
proyecto crece, lo natural es moverlo a una tarea programada (cron / Celery
beat) en vez de calcularlo en cada petición.

**3. Una respuesta cuenta también si es un "no".**
Que te rechacen sí es una respuesta (aunque no te hayan dicho que vieron el
CV explícitamente). Por eso `tasa_respuesta` cuenta "CV visto o más avanzado"
**o** "Rechazada", no solo lo primero.

**4. Sin Alembic todavía.**
El modelo de datos es una sola tabla y va a cambiar bastante al principio, así
que de momento las tablas se crean con `Base.metadata.create_all()` al
arrancar. En cuanto el esquema se estabilice (cuando empieces a separar
`companies`, `interviews`, `cv_versions` como sugiere el documento original),
merece la pena migrar a Alembic para no perder datos en cada cambio.

## Limitaciones conocidas / próximos pasos

- No hay autenticación (es un tracker personal, no falta según el MVP).
- El cálculo de "Sin respuesta" ocurre al consultar, no en segundo plano.
- Todo vive en una tabla (`applications`), como pedía el MVP. Separar
  `companies`, `interviews`, `technical_tests` y `cv_versions` es el
  siguiente paso natural si el proyecto crece.
- El dashboard es intencionadamente sencillo (HTML + JS + Chart.js por CDN,
  sin build step) para no meter una arquitectura de frontend innecesaria.
