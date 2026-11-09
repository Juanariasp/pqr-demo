param([int]$FrontendPort = 3000, [int]$BackendPort = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$pythonExe = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$nodeExe = (Get-Command node.exe).Source
$nextScript = Join-Path $projectRoot 'frontend\node_modules\next\dist\bin\next'
$runtimeDir = Join-Path $projectRoot '.local'
if (!(Test-Path -LiteralPath $pythonExe) -or !(Test-Path -LiteralPath $nextScript)) {
    throw 'Instala las dependencias siguiendo README.md antes de iniciar.'
}
foreach ($port in @($FrontendPort, $BackendPort)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "El puerto $port ya está ocupado. Usa otros puertos o detén tu ejecución anterior."
    }
}
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$backendProcess = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', $BackendPort) -WorkingDirectory (Join-Path $projectRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'backend.out.log') -RedirectStandardError (Join-Path $runtimeDir 'backend.err.log') -PassThru
$oldBackendUrl = $env:BACKEND_URL
$oldTelemetry = $env:NEXT_TELEMETRY_DISABLED
try {
    $env:BACKEND_URL = "http://127.0.0.1:$BackendPort"
    $env:NEXT_TELEMETRY_DISABLED = '1'
    $frontendProcess = Start-Process -FilePath $nodeExe -ArgumentList @("`"$nextScript`"", 'dev', '--hostname', '127.0.0.1', '--port', $FrontendPort) -WorkingDirectory (Join-Path $projectRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.out.log') -RedirectStandardError (Join-Path $runtimeDir 'frontend.err.log') -PassThru
} finally {
    $env:BACKEND_URL = $oldBackendUrl
    $env:NEXT_TELEMETRY_DISABLED = $oldTelemetry
}
@{ backend = $backendProcess.Id; frontend = $frontendProcess.Id; backendPort = $BackendPort; frontendPort = $FrontendPort } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimeDir 'processes.json')
Write-Output "Interfaz: http://127.0.0.1:$FrontendPort"
Write-Output "API: http://127.0.0.1:$BackendPort/docs"
Write-Output 'Los registros y los PID están en .local. Cierra los procesos al terminar tu demo.'
