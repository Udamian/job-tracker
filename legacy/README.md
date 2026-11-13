# PostgreSQL legado (solo backup y migración)

La app ya **no usa Docker ni PostgreSQL**. Este compose se conserva
únicamente para:

1. Hacer el respaldo final con `pg_dump`.
2. Ejecutar la migración a SQLite conservando `max_stage_reached`.

El nombre del proyecto y del volumen se mantienen igual que antes para no
crear una base vacía: `job-tracker` / `job-tracker_pgdata`.

```bash
docker compose -f legacy/docker-compose.yml up -d db
```

El puerto 5432 queda expuesto solo en local para que el script de migración
pueda conectarse desde Windows.

## Respaldo

```powershell
.\scripts\backup_postgres.ps1
```

Genera en `backups/`:

- `jobtracker_AAAA-MM-DD.sql` (pg_dump completo, incluye `max_stage_reached`)
- `candidaturas_AAAA-MM-DD.csv` (copia legible)

## Migración a SQLite

```powershell
.\.venv\Scripts\python.exe scripts\migrate_postgres_to_sqlite.py
```

## Limpieza (solo tras varias semanas sin incidencias)

```powershell
docker compose -f legacy/docker-compose.yml down
docker volume rm job-tracker_pgdata
```

No borres el volumen hasta haber validado la migración y tener el `.sql`
guardado en otro sitio.
