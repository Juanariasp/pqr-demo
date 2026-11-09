$projectRoot = Split-Path $PSScriptRoot -Parent
$portableGcloud = Join-Path $projectRoot '.tools\google-cloud-sdk\bin\gcloud.cmd'
if (Test-Path -LiteralPath $portableGcloud) {
    $script:GcloudExe = $portableGcloud
    $env:CLOUDSDK_PYTHON = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
    $env:CLOUDSDK_CONFIG = Join-Path $projectRoot '.local\gcloud'
} else {
    $script:GcloudExe = (Get-Command gcloud.cmd -ErrorAction Stop).Source
}
function Invoke-Gcloud {
    & $script:GcloudExe @args
    if ($LASTEXITCODE -ne 0) { throw "Falló gcloud: $($args[0..([Math]::Min(2, $args.Length - 1))] -join ' ')" }
}
