# Job Tracker — V3

Tracker personal de búsqueda de empleo: captura en una línea, estados con
un toque, Kanban, panel de detalle y estadísticas. Sin Docker, sin
servidores en segundo plano y con los datos en tu carpeta de usuario.

**Stack:** Python · FastAPI · SQLite · SQLAlchemy · Pydantic · Pandas ·
pywebview · PyInstaller · pytest.

---

## Arrancarlo

### 1. Como aplicación de escritorio (recomendado)

Construye el ejecutable una vez:

```powershell
.\build.ps1
```

Luego, doble clic en:

```text
dist\JobTracker\JobTracker.exe
```

La primera vez puedes crear un acceso directo en el escritorio con:

```powershell
.\install-shortcut.ps1
```

Al abrirlo:

- arranca uvicorn en `127.0.0.1` con un puerto libre,
- abre una ventana nativa (pywebview/WebView2),
- al cerrar la ventana, el servidor se apaga,
- un segundo doble clic enfoca la ventana existente en vez de lanzar otra,
- si falta WebView2, abre el navegador predeterminado.

### 2. Desde el código

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-desktop.txt
.\.venv\Scripts\python.exe desktop.py
```

### 3. Solo servidor (desarrollo)

```powershell
.\.venv\Scripts\python.exe -m app
```

Abre <http://127.0.0.1:8000/dashboard>. Sin `--reload` y sin `0.0.0.0`.

---

## Dónde viven los datos

Por defecto:

| Sistema | Ruta |
|---|---|
| Windows | `%LOCALAPPDATA%\JobTracker\jobtracker.db` |
| macOS | `~/Library/Application Support/JobTracker/jobtracker.db` |
| Linux | `~/.local/share/JobTracker/jobtracker.db` |

Actualizar el `.exe` o mover la carpeta del programa **no toca la base de
datos**. Puedes cambiarla con `JOBTRACKER_DATA_DIR` o `DATABASE_URL`
(ver `.env.example`).

> **Nota de desarrollo (Windows Store Python).** Si lanzas la app con el
> Python de Microsoft Store, Windows puede aplicar virtualización MSIX y
> redirigir las escrituras de `%LOCALAPPDATA%` a
> `%LOCALAPPDATA%\Packages\...\LocalCache`. La app empaquetada
> (`JobTracker.exe`) no sufre esa redirección. Para los datos reales usa el
> EXE; los tests usan una base temporal y no se ven afectados.

---

## Captura rápida

En la barra superior escribe `Empresa · Puesto` y pulsa `Enter`:

```text
Stripe · Backend Python
Stripe - Backend Python @entrevista
Cabify · Data Analyst
```

| Atajo | Acción |
|---|---|
| `Enter` | Guardar y dejar la barra lista para el siguiente |
| `Ctrl` + `K`, `/` o `N` | Saltar a la barra de captura |
| `Alt` + `A` | Alternar Hoy / Ayer (registro retroactivo) |
| `Esc` | Cerrar menús, sugerencias o panel de detalle |

- La fecha es automática (hoy). El botón **Hoy/Ayer** permite registrar
  algo retroactivo sin abrir un formulario.
- El estado por defecto es **Enviada**. Se puede cambiar con el chip de la
  barra o con `@estado` en el texto.
- Solo empresa y puesto son obligatorios. Todo lo demás (fuente, CV,
  modalidad, ubicación, URL, notas, fechas...) vive en el panel de detalle.
- El autocompletado sugiere empresas y puestos ya usados.
- Si ya aplicaste a esa empresa, avisa: *«Hace 12 días ya aplicaste a
  Stripe · Backend»*. No bloquea el guardado.
- Tras guardar o borrar aparece un aviso con **Deshacer**. No hay
  `confirm()`.

### Estados reconocidos en `@...`

Los cuatro estados del tablero son `enviada`, `contactado`, `entrevista` y
`rechazada`. También se aceptan los nombres antiguos (`guardada`,
`candidatura enviada`, `cv visto`, `cv`, `prueba`, `prueba tecnica`,
`oferta`, `sin respuesta`, `ghosted`) y se normalizan a uno de los cuatro.

---

## Interfaz

- **Tabla o Kanban.** El Kanban tiene cuatro columnas: **Enviada**,
  **Contactado**, **Entrevista** y **Rechazada**. Se ven todas a la vez
  (rejilla adaptable) y cada tarjeta se arrastra entre columnas.
- **Panel de detalle.** Clic en una fila o tarjeta. Ahí están todos los
  campos antiguos, las fechas, la etapa máxima y las notas. Se guarda con
  `PATCH` y también se puede deshacer.
- **Estancados.** Lista las candidaturas en *Enviada* o *Contactado* con
  más de 21 días desde el último movimiento. Acciones:
  - *Hacer seguimiento*: guarda la fecha de seguimiento y reinicia el contador.
  - *Rechazar*: mueve la candidatura a la columna *Rechazada*.
  - *Detalle*: abre el panel completo.
- **Rechazadas.** La columna *Rechazada* queda separada visualmente con
  acento rojo y muestra todas las candidaturas descartadas.
- **Ritmo diario/semanal.** Contador con meta editable (se guarda en el
  navegador).
- **Gráficos.** Ritmo semanal, embudo (Enviadas → Contactadas →
  Entrevistas → Rechazadas) y eficacia por perfil/CV.

---

## Estadísticas sin preguntar el tipo de puesto

La captura rápida no pregunta fuente, tipo de puesto ni CV. Para que el
gráfico *Eficacia por perfil y CV* siga funcionando, el backend deduce el
tipo de puesto del texto:

| Texto del puesto | Tipo deducido |
|---|---|
| `Ingeniero/a de datos Python-Pyspark` | Data Engineer |
| `Analista de Datos Junior / Python` | Data Analyst |
| `Desarrollador/a Python` | Python |
| `Junior Java` | Backend |
| `Formativo` | Otro |

Las reglas están en `app/inference.py`. Si no hay coincidencia, queda
`Otro`. El CV queda como `Sin especificar` si no se rellena en el detalle.

**El embudo sigue usando `max_stage_reached`.** Ese campo guarda la etapa
más alta alcanzada alguna vez, así que rechazar una candidatura no hace
retroceder el embudo.

---

## API principal

| Método | Ruta | Qué hace |
|---|---|---|
| POST | `/applications` | Crear (solo empresa/puesto obligatorios) |
| GET | `/applications` | Listar y filtrar |
| GET | `/applications/suggestions?q=` | Empresas y puestos ya usados |
| GET | `/applications/check?company=` | Aviso de duplicado |
| GET | `/applications/attention` | Panel de más de 21 días |
| GET | `/applications/{id}` | Detalle |
| PATCH | `/applications/{id}` | Editar / cambiar estado |
| DELETE | `/applications/{id}` | Borrar y devolver el registro |
| POST | `/applications/restore` | Deshacer un borrado |
| GET | `/applications/export/csv` | Exportar CSV |
| GET | `/applications/export/txt` | Exportar TXT |
| GET | `/stats/kpis` | Totales, hoy, semana, tasas... |
| GET | `/stats/funnel` | Embudo |
| GET | `/stats/weekly` | Candidaturas por semana |
| GET | `/stats/by-type` | Eficacia por tipo/CV |

Documentación interactiva: `/docs`.

---

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Los tests usan SQLite en memoria y no tocan la base real.

---

## Migración desde PostgreSQL (ya realizada)

El 12/11/2026 se hizo el respaldo y la migración:

1. `pg_dump` completo -> `backups/jobtracker_2026-11-12.sql`
2. CSV legible -> `backups/candidaturas_2026-11-12_api.csv`
3. Migración -> `%LOCALAPPDATA%\JobTracker\jobtracker.db`

Resultado validado: **16 filas**, mismos IDs, mismas fechas, mismos
`max_stage_reached`, mismas notas y URLs. Tras normalizar los estados
antiguos al modelo de cuatro, la distribución de esas 16 filas quedó:

- Enviada: 12
- Rechazada: 4

Las 16 filas producen 15 huellas únicas de empresa + puesto + fecha porque
hay dos registros idénticos de *Profile Software Services*; el script
compara multiconjuntos, así que la duplicidad se conserva.

### Repetir la migración

```powershell
# 1. Respaldo (no borra el volumen)
.\scripts\backup_postgres.ps1

# 2. Migración (falla si el destino ya tiene filas)
.\.venv\Scripts\python.exe scripts\migrate_postgres_to_sqlite.py

# Si necesitas reemplazar el destino:
.\.venv\Scripts\python.exe scripts\migrate_postgres_to_sqlite.py --overwrite
```

El script valida total, IDs, conteo por estado, distribución de etapa y
huella empresa + puesto + fecha. Se usa `pg_dump`/PostgreSQL y no el CSV
porque el CSV de exportación no incluye `max_stage_reached`.

---

## Empaquetado

```powershell
.\build.ps1
```

- PyInstaller en modo **onedir** (arranca más rápido y da menos falsos
  positivos de antivirus que onefile).
- Icono: `app/static/favicon.ico`.
- Datos de la app en `%LOCALAPPDATA%\JobTracker\`, fuera de `dist\`.

## Docker legado

Docker ya no es necesario. `Dockerfile` y `docker-compose.yml` están en
`legacy/`. El compose legado solo levanta PostgreSQL para respaldos o para
repetir la migración, y mantiene el volumen original
`job-tracker_pgdata`.

No borres el volumen hasta llevar varias semanas usando SQLite sin
incidencias:

```powershell
docker compose -f legacy/docker-compose.yml down
docker volume rm job-tracker_pgdata
```

---

## Decisiones de diseño

**`max_stage_reached` en vez de historial.** El embudo es acumulado:
cuenta cuántas candidaturas llegaron *alguna vez* a cada etapa. Una tabla
`status_history` sería el siguiente paso si el proyecto crece.

**«Estancados» no cambia nada solo.** Antes, consultar la lista cambiaba
estados a los 21 días. Ahora el sistema solo avisa en *Estancados* y el
usuario decide si hace seguimiento o rechaza. Es explícito y reversible.

**Una respuesta cuenta también si es un «no».** La tasa de respuesta
incluye *Contactado o más* **o** *Rechazada*.

**Sin Alembic todavía.** Hay una sola tabla. `create_all()` crea el
esquema y `ensure_sqlite_columns()` añade columnas nuevas a bases SQLite
antiguas. Cuando el esquema se estabilice, Alembic será el siguiente paso.

**Sin autocompletado desde URL.** LinkedIn e InfoJobs bloquean el scraping
y el resultado sería frágil. Se descartó a propósito.

---

## Limitaciones conocidas

- Sin autenticación: es un tracker personal en `127.0.0.1`.
- El respaldo automático no está programado; usa
  `scripts/backup_postgres.ps1` mientras conserves PostgreSQL, o copia el
  `.db` de `%LOCALAPPDATA%\JobTracker\`.
- Si WebView2 no está instalado, el respaldo en navegador mantiene el
  proceso vivo hasta cerrarlo manualmente.
- El dashboard es HTML + JS + Chart.js por CDN, sin build step.
