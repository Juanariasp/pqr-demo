# Nexo PQR

Plataforma de demostración para una entrevista técnica. Permite registrarse, enviar una petición, queja o reclamo mediante texto, Word o PDF, y consultar la clasificación, prioridad y respuesta sugerida. Todos los ejemplos son ficticios.

## Ejecución local en Windows

Requisitos: Python 3.12 y Node.js 22 o superior. El modo local funciona sin cuentas cloud ni claves y se identifica en pantalla como **análisis por reglas**. Para ensayar el flujo con IA real, configura `AI_MODE=gemini` y tu clave gratuita en `backend/.env`.

```powershell
cd 'C:\Users\Juanes \Documents\Personal\ju'
py -3.12 -m venv backend\.venv
& .\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
cd frontend
npm.cmd ci
cd ..
& .\scripts\start-local.ps1 -BackendPort 8001
& .\backend\.venv\Scripts\python.exe scripts\seed_demo.py http://127.0.0.1:8001
```

Esta sesión ya tiene las dependencias instaladas. Abre `http://127.0.0.1:3000`. La documentación interactiva de la API está en `http://127.0.0.1:8001/docs`.

Cuenta ficticia local después de ejecutar la carga: **demo@nexo.test / NexoDemo2026!**. También puedes crear otra cuenta desde la interfaz. Esa contraseña es solo un ejemplo público de uso local; el script de carga se niega a crear cuentas en Cloud.

`start-local.ps1` inicia dos procesos ocultos y guarda sus PID y registros en `.local/`. No termina procesos que ocupen los puertos. Puedes usar `-FrontendPort 3001 -BackendPort 8002`. Para desarrollo en terminales separadas:

```powershell
# Terminal 1, desde backend
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
# Terminal 2, desde frontend
$env:BACKEND_URL='http://127.0.0.1:8001'
npm.cmd run dev
```

## Arquitectura

```text
Navegador
    │ HTTPS y cookie HttpOnly
    ▼
Next.js / React (Cloud Run: pqr-web, interfaz pública)
    │ Proxy del mismo origen + identidad IAM del servicio
    │ Token Firebase de la sesión
    ▼
FastAPI (Cloud Run: pqr-api, requiere invocador IAM)
    ├── Firebase Authentication: registro y validación de identidad
    ├── Firestore: PQR, texto original, texto editado y resultado
    ├── Cloud Storage privado: documentos Word y PDF
    └── Coordinador Google ADK SequentialAgent
            Clasificador → Analista → Redactor
                         Gemini API gratuita
```

La API y la interfaz son servicios independientes. Next.js conserva el ID token Firebase en una cookie HttpOnly y lo adjunta al llamar a FastAPI. Cloud Run valida por separado la identidad del frontend mediante `X-Serverless-Authorization`; FastAPI valida el usuario y la propiedad del recurso. Las credenciales del servicio proceden de su identidad de ejecución, sin archivos de cuenta de servicio.

La configuración actual utiliza tres proyectos: `project-2e2f3efa-3e25-45e6-b44` para Cloud Run y archivos durante la prueba gratuita; `pqr-demo-data-53950210571` para Firebase Authentication y Firestore en Spark sin facturación; y el proyecto Gemini existente `gen-lang-client-0783494437`, también sin facturación. Esta separación evita actualizar Firebase a Blaze y mantiene gratuitas las APIs de datos e IA dentro de sus cuotas. `FIREBASE_PROJECT_ID` identifica el proyecto de datos y autenticación; `GOOGLE_CLOUD_PROJECT` identifica el proyecto de ejecución.

La pantalla de autenticación es pública; los datos de la aplicación solo se cargan después de validar la sesión. No hay acceso directo del navegador a Firestore o Storage. `firestore.rules` deniega los SDK de cliente; el backend accede mediante IAM.

El modo local sustituye Firebase/Firestore/Storage por contraseñas con PBKDF2, tokens firmados, SQLite y archivos en `backend/.data/`. **Cloud Run rechaza iniciar en modo local**. No se presenta el motor de reglas como Google ADK ni se utiliza como reemplazo silencioso si Gemini falla.

## Estructura

```text
backend/app/           API, autenticación, persistencia, extracción y agentes
backend/tests/         Pruebas del flujo, errores e aislamiento de usuarios
frontend/app/          Interfaz Next.js, estilos y proxy con cookie HttpOnly
scripts/               Inicio local, ejemplos y despliegue
samples/               Documentos ficticios y entradas inválidas
docs/                  Guion de entrevista y despliegue
.github/workflows/     CI para backend e interfaz
```

## Flujo y decisiones

1. El usuario se registra o inicia sesión. La sesión dura una hora; se pide iniciar sesión nuevamente al vencer. El prototipo no implementa recuperación de contraseña ni renovación automática.
2. Escribe un asunto y un texto de 20 a 20.000 caracteres o carga un `.docx`/`.pdf` de hasta 5 MB. El backend valida extensión, contenido real, tamaño, estructura, límites de páginas y expansión ZIP. Rechaza Word con macros u objetos incrustados; nunca ejecuta contenido activo. La extracción no sigue enlaces.
3. La carga devuelve un texto editable. El original y el texto confirmado se conservan por separado. Un PDF sin texto seleccionable devuelve un mensaje específico; OCR queda pendiente. El extractor conserva párrafos y texto de tablas cuando el formato lo permite, sin prometer reproducir la maquetación del archivo.
4. La creación guarda la PQR como `recibida`. La interfaz invoca el análisis en una petición separada. Los estados son `recibida`, `procesando`, `completada` y `error`.
5. El coordinador ADK ejecuta tres agentes en orden. Cada salida se valida mediante Pydantic. Se guarda el resultado únicamente cuando el flujo completo finaliza. El texto de la PQR se trata como contenido no confiable y los agentes no tienen herramientas de ejecución ni acceso a sistemas externos.
6. El análisis permanece dentro de la petición HTTP, con límite de 90 segundos y timeout Cloud Run de 120 segundos. No depende de tareas de fondo en una instancia sin CPU. Una transacción impide análisis concurrentes. Una reserva que lleve dos minutos puede recuperarse con un reintento. Repetir el análisis de una solicitud completada devuelve el resultado existente.
7. Los documentos sin asociar vencen a las 24 horas y se limpian cuando su propietario realiza otra carga. Una instalación real necesitaría programar la limpieza global; el prototipo no agrega Cloud Scheduler. Los documentos asociados no se eliminan automáticamente.

### Criterios

| Campo | Criterio |
|---|---|
| Petición | Solicitud de información, certificados o una acción |
| Queja | Inconformidad con la atención o calidad del servicio |
| Reclamo | Solicitud de corregir un cobro o un incumplimiento |
| Otra | Sugerencias o contenido que no encaja en las anteriores |
| Alta | Servicio bloqueado, interrupción total o urgencia explícita |
| Media | Incidente o inconformidad |
| Baja | Información general o sugerencias |

La respuesta siempre es una sugerencia para revisión humana. No confirma operaciones realizadas, devoluciones ni plazos. ADK hace tres llamadas de modelo por PQR; las cuotas gratuitas pueden agotarse y dependen de la cuenta. Se usa `gemini-3.5-flash-lite`, configurable mediante `GEMINI_MODEL` y verificado con una llamada real en esta cuenta.

## Configuración

Copia `backend/.env.example` a `backend/.env` y `frontend/.env.example` a `frontend/.env.local` cuando quieras personalizar la ejecución. Reinicia los procesos después de cambiar variables. No compartas `.env`, `.local/` ni claves de cuentas de servicio.

| Servicio | Variables |
|---|---|
| Backend | `APP_MODE=local` o `cloud`, `AI_MODE=rules` o `gemini` |
| Cloud | `GOOGLE_CLOUD_PROJECT`, `FIREBASE_PROJECT_ID`, `FIREBASE_WEB_API_KEY`, `STORAGE_BUCKET` |
| IA | `GOOGLE_API_KEY`, `GEMINI_MODEL`, `ANALYSIS_TIMEOUT_SECONDS=90` |
| Documentos | `MAX_UPLOAD_MB=5`, `MAX_TEXT_CHARS=20000` |
| Frontend | `BACKEND_URL`, `BACKEND_IAM_AUTH=true` en Cloud Run, `MAX_UPLOAD_MB=5` |

La clave web Firebase identifica el proyecto; la autorización de datos depende de tokens, propiedad e IAM. La clave Gemini es un secreto y solo debe existir en el backend y Secret Manager.

## API

| Método y ruta | Uso |
|---|---|
| `GET /health` | Modo de ejecución, motor de análisis y límite de carga |
| `POST /auth/register` | Registro con correo y contraseña |
| `POST /auth/login` | Inicio de sesión y emisión de token |
| `GET /auth/me` | Usuario actual |
| `POST /uploads` | Validación, almacenamiento temporal y extracción de Word/PDF |
| `POST /pqrs` | Crear PQR con texto y `upload_id` opcional |
| `GET /pqrs` | Historial del usuario autenticado |
| `GET /pqrs/{id}` | Detalle de una PQR propia |
| `POST /pqrs/{id}/analyze` | Analizar o reintentar |
| `GET /pqrs/{id}/result` | Estado y resultado |
| `GET /pqrs/{id}/file` | Descargar el original después de validar la propiedad |

Las rutas privadas requieren `Authorization: Bearer <token>`. El proxy web evita que JavaScript tenga que guardar tokens. `/api/auth/logout` borra la cookie del navegador. Consultar un recurso ajeno devuelve 404.

## Verificación

```powershell
cd backend
& .\.venv\Scripts\python.exe -m ruff check app tests
& .\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm.cmd run build
```

Las pruebas cubren flujo de texto, autenticación, propiedad de solicitudes y documentos, descarga del original, edición del texto extraído, archivos vacíos/corruptos/no permitidos/grandes, PDF sin texto, error del modelo y reintento, idempotencia de resultados y rechazo del modo local en Cloud Run. El flujo real de Gemini y la persistencia cloud necesitan una comprobación integrada adicional después del despliegue; los tests locales no los simulan como si hubieran ocurrido.

Los documentos de `samples/` sirven para demostrar los casos válidos e inválidos. `scripts/generate_samples.py` los regenera con `python-docx`, `reportlab` y Pillow; estas dos últimas dependencias solo se requieren para regenerar los ejemplos, no para ejecutar la aplicación.

GitHub Actions ejecuta las pruebas, el análisis estático y la compilación en cada push/PR. No despliega automáticamente ni almacena claves cloud en GitHub. Los Dockerfiles utilizan las versiones fijadas en `requirements.lock.txt` y `package-lock.json`, y ejecutan como usuario sin privilegios.

La verificación integrada real del despliegue se puede repetir con `backend/.venv/Scripts/python.exe scripts/smoke-cloud.py`. Crea dos cuentas ficticias con contraseñas aleatorias solo en memoria y comprueba documentos, análisis Gemini, descarga e aislamiento de usuarios. Guarda evidencia sin credenciales en `.local/cloud-validation.json`. Consulta el resultado de esta entrega en [VALIDATION.md](docs/VALIDATION.md).

## Cloud y entrevista

Consulta [el despliegue](docs/DEPLOY.md) y [el guion para la demo](docs/DEMO.md). No se garantiza costo cero para Cloud Run, Cloud Build, Artifact Registry, Firestore, Secret Manager o Storage: tienen condiciones de cobro propias. Mantener Gemini en un proyecto sin facturación permite usar el nivel gratuito disponible, sin activar automáticamente su modalidad de pago.

## Limitaciones y mejoras

Prototipo para pocos usuarios y solo datos ficticios: sin OCR, antivirus, cola durable, paginación, alertas de operación, auditoría empresarial, políticas legales de conservación, WAF ni rate limiting distribuido. No implementa recuperación de contraseña ni email de verificación. El historial carga todos los registros del propietario; escalarlo requiere paginación. El procesamiento puede requerir reintento tras una caída y los fallos de almacenamiento entre la reserva de un archivo y la creación de la PQR requieren conciliación manual. Los documentos abandonados se limpian de forma diferida, no mediante una tarea programada.

Mejoras prioritarias: limpieza programada, límites por usuario, renovación de sesión, verificación de correo, pruebas cloud automatizadas, OCR con consentimiento y una cola durable si aumenta el volumen.

## Fuentes oficiales

- [Next.js y requisitos de instalación](https://nextjs.org/docs/app/getting-started/installation)
- [Google ADK y SequentialAgent](https://google.github.io/adk-docs/agents/workflow-agents/sequential-agents/)
- [Precios y nivel gratuito de Gemini](https://ai.google.dev/gemini-api/docs/pricing)
- [Facturación de Gemini](https://ai.google.dev/gemini-api/docs/billing)
- [Firebase y verificación de ID tokens](https://firebase.google.com/docs/auth/admin/verify-id-tokens)
- [Cloud Run y despliegue desde código](https://docs.cloud.google.com/run/docs/deploying-source-code)
