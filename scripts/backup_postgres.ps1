# Respaldo previo al cambio a SQLite.
# Uso: .\scripts\backup_postgres.ps1
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$compose = Join-Path $root "legacy\docker-compose.yml"
$dir = Join-Path $root "backups"
$stamp = Get-Date -Format "yyyy-MM-dd"

New-Item -ItemType Directory -Force -Path $dir | Out-Null

Write-Host "Levantando PostgreSQL legado..."
docker compose -f $compose up -d db
if ($LASTEXITCODE -ne 0) { throw "No se pudo levantar el servicio db." }

Write-Host "Esperando a que PostgreSQL esté listo..."
for ($i = 0; $i -lt 30; $i++) {
    docker compose -f $compose exec -T db pg_isready -U jobtracker -d jobtracker | Out-Null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 1
}

$sql = Join-Path $dir "jobtracker_$stamp.sql"
Write-Host "pg_dump -> $sql"
docker compose -f $compose exec -T db pg_dump -U jobtracker -d jobtracker --no-owner --clean --if-exists |
    Out-File -FilePath $sql -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "pg_dump falló." }

$csv = Join-Path $dir "candidaturas_$stamp.csv"
Write-Host "CSV -> $csv"
$consulta = @"
\copy (SELECT id, company AS empresa, position AS puesto, status AS estado, job_type AS tipo_puesto, cv_version AS cv_usado, source AS fuente, modality AS modalidad, location AS ubicacion, found_date AS fecha_encontrada, applied_date AS fecha_candidatura, response_date AS fecha_respuesta, url, notes AS notas, last_update AS ultima_actualizacion, max_stage_reached AS etapa_maxima FROM applications ORDER BY id) TO STDOUT WITH CSV HEADER
"@
docker compose -f $compose exec -T db psql -U jobtracker -d jobtracker -c $consulta |
    Out-File -FilePath $csv -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "La exportación CSV falló." }

Write-Host ""
Write-Host "Respaldo completado."
Write-Host "  $sql"
Write-Host "  $csv"
Write-Host "El volumen job-tracker_pgdata NO se ha tocado."
