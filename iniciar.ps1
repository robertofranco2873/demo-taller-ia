# Arranca AutoServicio Demo (datos ficticios). Normalmente se usa con doble clic en "Iniciar AutoServicio.bat".
# Uso manual:  .\iniciar.ps1  [-Puerto 8000]  [-SinNavegador]
# 1) Prepara lo que falte (entorno virtual, dependencias, frontend compilado).
# 2) Libera el puerto si lo ocupa un servidor anterior de Python/uvicorn.
# 3) Arranca el servidor y abre el navegador cuando está listo.
param([int]$Puerto = 8000, [switch]$SinNavegador)

$ErrorActionPreference = "Stop"
$raiz = $PSScriptRoot
Set-Location $raiz
$host.UI.RawUI.WindowTitle = "AutoServicio Demo (no cierres esta ventana)"
$python = Join-Path $raiz ".venv\Scripts\python.exe"
$nodeDir = Join-Path $env:LOCALAPPDATA "Programs\nodejs"
if (Test-Path $nodeDir) { $env:Path = "$nodeDir;$env:Path" }

function Paso($texto) { Write-Host "`n>> $texto" -ForegroundColor Magenta }

try {
    # ---------- 1. Preparación (solo la primera vez) ----------
    if (-not (Test-Path $python)) {
        Paso "Creando entorno de Python (solo la primera vez)..."
        py -3.12 -m venv .venv
        & $python -m pip install --upgrade pip -q
        & $python -m pip install -r requirements.txt -q
    }
    & $python -c "import fastapi, uvicorn, bcrypt, jwt, fpdf" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Paso "Instalando dependencias de Python..."
        & $python -m pip install -r requirements.txt -q
    }
    if (-not (Test-Path "frontend\dist\index.html")) {
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            throw "Falta Node.js para compilar la interfaz. Instálalo desde https://nodejs.org (versión LTS) y vuelve a intentar."
        }
        Paso "Compilando la interfaz (solo la primera vez, tarda unos minutos)..."
        Push-Location frontend
        if (-not (Test-Path "node_modules")) { npm install --no-audit --no-fund --loglevel=error }
        npm run build
        Pop-Location
    }

    # ---------- 2. Liberar el puerto ----------
    foreach ($c in @(Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue)) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($null -eq $proc) { continue }
        if ($proc.ProcessName -match "python|uvicorn") {
            Paso "Cerrando servidor anterior en el puerto $Puerto (PID $($proc.Id))..."
            Stop-Process -Id $proc.Id -Force
            Start-Sleep -Seconds 1
        } else {
            throw "El puerto $Puerto lo usa '$($proc.ProcessName)' (PID $($proc.Id)), que no es de este proyecto. No lo cierro. Usa otro puerto: .\iniciar.ps1 -Puerto 8010"
        }
    }

    # ---------- 3. Abrir el navegador cuando el servidor responda ----------
    $url = "http://localhost:$Puerto"
    if (-not $SinNavegador) {
        Start-Job -ArgumentList $url -ScriptBlock {
            param($u)
            for ($i = 0; $i -lt 60; $i++) {
                try { Invoke-WebRequest "$u/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; Start-Process $u; return } catch { Start-Sleep 1 }
            }
        } | Out-Null
    }

    Write-Host ""
    Write-Host "  AutoServicio Demo  ·  datos ficticios" -ForegroundColor Yellow
    Write-Host "  Abriendo $url  (usuarios: gerente / recepcion / tecnico, clave demo123)"
    Write-Host "  Para detener la app, cierra esta ventana o presiona Ctrl+C." -ForegroundColor DarkGray
    Write-Host ""
    & $python -m uvicorn api.main:app --port $Puerto
}
catch {
    Write-Host "`nNo se pudo iniciar: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Presiona Enter para cerrar"
    exit 1
}
