$ErrorActionPreference = "Continue"

$root = $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "No existe .venv. Crealo con: python -m venv .venv"
}

Write-Host "Instalando dependencias de escritorio y empaquetado..."
& $python -m pip install -r requirements-dev.txt 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "Fallo pip install." }

Write-Host "Construyendo dist\JobTracker\JobTracker.exe ..."
& $python -m PyInstaller --noconfirm --clean jobtracker.spec 2>&1 | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw "PyInstaller termino con error." }

Write-Host ""
Write-Host "Listo: $root\dist\JobTracker\JobTracker.exe"
Write-Host "La base de datos vive en %LOCALAPPDATA%\JobTracker\ y no se toca al actualizar el EXE."
