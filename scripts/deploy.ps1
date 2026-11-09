param(
    [string]$ProjectId = 'project-2e2f3efa-3e25-45e6-b44',
    [string]$Region = 'us-central1',
    [string]$GeminiKeyFile = '.local\gemini-api-key.txt',
    [string]$GeminiModel = 'gemini-3.5-flash-lite',
    [switch]$TrialConfirmed
)
$ErrorActionPreference = 'Stop'
if (!$TrialConfirmed) { throw 'Confirma en Billing que la cuenta sigue en Free trial sin actualización a pago. Usa -TrialConfirmed únicamente después de esa revisión.' }
. "$PSScriptRoot\cloud-context.ps1"
Set-Location -LiteralPath $projectRoot
$configPath = Join-Path $projectRoot '.local\cloud-config.json'
if (!(Test-Path -LiteralPath $configPath)) { throw 'Ejecuta configure-firebase.py primero.' }
if (!(Test-Path -LiteralPath $GeminiKeyFile)) { throw 'Guarda tu clave Gemini de nivel gratuito en .local\gemini-api-key.txt, sin subirla a Git.' }
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
if ($config.project_id -ne $ProjectId) { throw 'La configuración Firebase pertenece a otro proyecto.' }
$firebaseProject = $config.firebase_project_id
if (!$firebaseProject) { throw 'Configura FIREBASE_PROJECT_ID en cloud-config.json.' }
$firebaseBilling = Invoke-Gcloud billing projects describe $firebaseProject --format=json | ConvertFrom-Json
if ($firebaseBilling.billingEnabled) { throw 'El proyecto Firebase debe permanecer sin facturación.' }
$projectNumber = Invoke-Gcloud projects describe $ProjectId --format='value(projectNumber)'
$apiAccount = "pqr-api@$ProjectId.iam.gserviceaccount.com"
$webAccount = "pqr-web@$ProjectId.iam.gserviceaccount.com"
Invoke-Gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com firestore.googleapis.com identitytoolkit.googleapis.com secretmanager.googleapis.com --project=$ProjectId --quiet
$accounts = Invoke-Gcloud iam service-accounts list --project=$ProjectId --format='value(email)'
if ($apiAccount -notin $accounts) { Invoke-Gcloud iam service-accounts create pqr-api --display-name='Nexo PQR backend' --project=$ProjectId --quiet }
if ($webAccount -notin $accounts) { Invoke-Gcloud iam service-accounts create pqr-web --display-name='Nexo PQR frontend' --project=$ProjectId --quiet }
Invoke-Gcloud projects add-iam-policy-binding $firebaseProject --member="serviceAccount:$apiAccount" --role=roles/datastore.user --condition=None --quiet | Out-Null
Invoke-Gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$projectNumber-compute@developer.gserviceaccount.com" --role=roles/run.builder --condition=None --quiet | Out-Null
$databases = Invoke-Gcloud firestore databases list --project=$firebaseProject --format='value(name)'
if (!($databases | Where-Object { $_ -match '/databases/\(default\)$' })) {
    Invoke-Gcloud firestore databases create --database='(default)' --location=$Region --type=firestore-native --project=$firebaseProject --quiet
}
$bucket = "gs://$($config.storage_bucket)"
$buckets = Invoke-Gcloud storage buckets list --project=$ProjectId --format='value(name)'
if ($config.storage_bucket -notin $buckets) {
    Invoke-Gcloud storage buckets create $bucket --location=$Region --uniform-bucket-level-access --public-access-prevention --project=$ProjectId --quiet
}
Invoke-Gcloud storage buckets add-iam-policy-binding $bucket --member="serviceAccount:$apiAccount" --role=roles/storage.objectUser --quiet | Out-Null
$secrets = Invoke-Gcloud secrets list --project=$ProjectId --format='value(name)'
if (!($secrets | Where-Object { $_ -match '(^|/)pqr-gemini-api-key$' })) {
    Invoke-Gcloud secrets create pqr-gemini-api-key --replication-policy=automatic --project=$ProjectId --quiet
}
Invoke-Gcloud secrets versions add pqr-gemini-api-key --data-file=$GeminiKeyFile --project=$ProjectId --quiet | Out-Null
$secretVersion = Invoke-Gcloud secrets versions list pqr-gemini-api-key --filter='state=ENABLED' --sort-by='~createTime' --limit=1 --format='value(name)' --project=$ProjectId
$secretVersion = ($secretVersion -split '/')[-1]
Invoke-Gcloud secrets add-iam-policy-binding pqr-gemini-api-key --member="serviceAccount:$apiAccount" --role=roles/secretmanager.secretAccessor --condition=None --project=$ProjectId --quiet | Out-Null
$backendEnv = @{ APP_MODE='cloud'; AI_MODE='gemini'; GOOGLE_CLOUD_PROJECT=$ProjectId; FIREBASE_PROJECT_ID=$firebaseProject; FIREBASE_WEB_API_KEY=$config.firebase_web_api_key; STORAGE_BUCKET=$config.storage_bucket; GEMINI_MODEL=$GeminiModel; MAX_UPLOAD_MB='5'; ANALYSIS_TIMEOUT_SECONDS='90' }
$backendEnv | ConvertTo-Json | Set-Content -LiteralPath '.local\backend-env.json' -Encoding utf8
Invoke-Gcloud run deploy pqr-api --source=backend --region=$Region --project=$ProjectId --service-account=$apiAccount --no-allow-unauthenticated --min-instances=0 --max-instances=1 --concurrency=8 --cpu=1 --memory=512Mi --timeout=120 --env-vars-file=.local/backend-env.json --set-secrets="GOOGLE_API_KEY=pqr-gemini-api-key:$secretVersion" --quiet
$apiUrl = Invoke-Gcloud run services describe pqr-api --region=$Region --project=$ProjectId --format='value(status.url)'
Invoke-Gcloud run services add-iam-policy-binding pqr-api --member="serviceAccount:$webAccount" --role=roles/run.invoker --region=$Region --project=$ProjectId --quiet | Out-Null
Invoke-Gcloud run deploy pqr-web --source=frontend --region=$Region --project=$ProjectId --service-account=$webAccount --allow-unauthenticated --min-instances=0 --max-instances=1 --concurrency=20 --cpu=1 --memory=512Mi --timeout=120 --set-env-vars="BACKEND_URL=$apiUrl,BACKEND_IAM_AUTH=true,NEXT_TELEMETRY_DISABLED=1" --quiet
$webUrl = Invoke-Gcloud run services describe pqr-web --region=$Region --project=$ProjectId --format='value(status.url)'
@{ frontend=$webUrl; backend=$apiUrl; project=$ProjectId; region=$Region } | ConvertTo-Json | Set-Content -LiteralPath '.local\deployment.json'
Write-Output "Aplicación publicada: $webUrl"
Write-Output 'La API solo admite invocaciones IAM del servicio frontend; los datos además requieren un token Firebase válido.'
