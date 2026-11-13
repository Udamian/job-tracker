$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$exe = Join-Path $root "dist\JobTracker\JobTracker.exe"

if (-not (Test-Path $exe)) {
    throw "Primero construye el EXE con .\build.ps1 (no existe $exe)"
}

$escritorio = [Environment]::GetFolderPath("Desktop")
$acceso = Join-Path $escritorio "Job Tracker.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($acceso)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Join-Path $root "dist\JobTracker"
$shortcut.IconLocation = $exe
$shortcut.Description = "Job Tracker"
$shortcut.Save()

Write-Host "Acceso directo creado: $acceso"
