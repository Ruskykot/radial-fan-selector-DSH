# Запуск fan-selector одной командой: MCP-сервер (:8000) + UI (:8080) + REST (:8001).
#   .\start.ps1            — поднять всё (собрать web/, если dist отсутствует)
#   .\start.ps1 -Build     — принудительно пересобрать web/
#   .\start.ps1 -NoRest    — не поднимать REST
param(
    [switch]$Build,
    [switch]$NoRest
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$dsh = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies"

function Resolve-Tool([string]$envName, [string]$bundled, [string]$fallback) {
    $v = [Environment]::GetEnvironmentVariable($envName)
    if ($v) { return $v }
    if (Test-Path $bundled) { return $bundled }
    return $fallback
}

$python = Resolve-Tool "PYTHON" "$dsh\python\python.exe" "python"
$node   = Resolve-Tool "NODE"   "$dsh\node\bin\node.exe"    "node"
$pnpm   = Resolve-Tool "PNPM"   "$dsh\pnpm\bin\pnpm.mjs"    "pnpm"

# --- Сборка web/ ---
$dist = Join-Path $root "web\dist"
if ($Build -or -not (Test-Path (Join-Path $dist "index.html"))) {
    Write-Host "[build] web/ ..."
    Push-Location (Join-Path $root "web")
    try {
        & $node $pnpm build
        if ($LASTEXITCODE -ne 0) { throw "сборка web/ завершилась с ошибкой" }
    } finally { Pop-Location }
}

# --- 1) MCP-сервер (streamable-http :8000, с CORS) ---
$mcp = Start-Process -FilePath $python -ArgumentList @("mcp_stdio.py", "streamable-http") `
    -WorkingDirectory $root -PassThru -WindowStyle Hidden
Write-Host "[mcp]  PID $($mcp.Id)  http://127.0.0.1:8000/mcp"

# --- 2) UI (статическая раздача web/dist :8080) ---
$ui = Start-Process -FilePath $python `
    -ArgumentList @("-m", "http.server", "8080", "--directory", "web/dist", "--bind", "127.0.0.1") `
    -WorkingDirectory $root -PassThru -WindowStyle Hidden
Write-Host "[ui]   PID $($ui.Id)  http://127.0.0.1:8080"

# --- 3) REST (фолбэк :8001) ---
if (-not $NoRest) {
    $rest = Start-Process -FilePath $python -ArgumentList @("-m", "mcp_server.rest") `
        -WorkingDirectory $root -PassThru -WindowStyle Hidden
    Write-Host "[rest] PID $($rest.Id)  http://127.0.0.1:8001/select"
}

Write-Host ""
Write-Host "UI:   http://127.0.0.1:8080"
Write-Host "MCP:  http://127.0.0.1:8000/mcp"
Write-Host ""
Write-Host "Остановка: Stop-Process -Id $($mcp.Id),$($ui.Id)$(if(-not $NoRest){",$($rest.Id)"})"
