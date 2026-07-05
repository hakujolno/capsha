$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Virtual environment not found. Create .venv and install requirements.txt first."
}

Push-Location $ProjectRoot
try {
    & $Python "scripts\generate_icon.py"
    if ($LASTEXITCODE -ne 0) { throw "Icon generation failed." }

    & $Python -m PyInstaller --noconfirm --clean "capsha.spec"
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

    $Executable = Join-Path $ProjectRoot "dist\Capsha.exe"
    if (-not (Test-Path -LiteralPath $Executable)) {
        throw "Build completed without dist\Capsha.exe."
    }

    Write-Host "Release ready: $Executable"
}
finally {
    Pop-Location
}
