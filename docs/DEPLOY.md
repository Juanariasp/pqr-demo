# Despliegue en Google Cloud

Proyecto de ejecución: `project-2e2f3efa-3e25-45e6-b44`. Proyecto Firebase Spark sin facturación: `pqr-demo-data-53950210571`. Región inicial: `us-central1`. La interfaz y la API se despliegan en Cloud Run por separado, cada una con cero instancias mínimas y una instancia máxima.

El 8 de noviembre de 2026 se verificó en la consola que la cuenta de ejecución seguía en **Free trial**, con crédito disponible, fin el **7 de febrero de 2027** y sin cargos automáticos mientras no se actualice a una cuenta de pago. La demo puede consumir ese crédito. No pulses Upgrade ni vincules facturación al proyecto Firebase o Gemini para esta entrega. Al terminar la prueba o el crédito, los recursos de Cloud se detienen. Revisa de nuevo esa condición antes de cada despliegue; `-TrialConfirmed` exige confirmarla.

## Revisar antes de ejecutar

Lee `scripts/deploy.ps1`: crea dos identidades de servicio, Firestore nativo en el proyecto Spark, un bucket privado y un secreto Gemini en el proyecto de ejecución. Concede al backend acceso a Firestore en el proyecto de datos, al bucket de la demo y al secreto; al frontend únicamente permiso de invocar la API. Publica la interfaz web y mantiene la API protegida por IAM. El backend valida adicionalmente el token Firebase y la propiedad del recurso.

El proyecto necesita facturación. Cloud Build, Artifact Registry, Cloud Run, Firestore, Storage y Secret Manager pueden generar cargos fuera de sus cuotas gratuitas. Una instancia máxima reduce capacidad, pero **no fija un límite monetario**. Los presupuestos son alertas, no cortes automáticos. Revisa Billing después de la demo y retira los recursos cuando dejen de usarse.

## Configurar acceso y Firebase

Instala la CLI oficial de Google Cloud o utiliza la copia descargada en `.tools/google-cloud-sdk`. En esta sesión se utiliza una configuración aislada en `.local/gcloud`. Las sesiones de autenticación y los archivos de esa carpeta no se suben a Git.

```powershell
. .\scripts\cloud-context.ps1
Invoke-Gcloud auth login
Invoke-Gcloud services enable firebase.googleapis.com identitytoolkit.googleapis.com firestore.googleapis.com --project=pqr-demo-data-53950210571
& .\backend\.venv\Scripts\python.exe scripts\configure-firebase.py --project pqr-demo-data-53950210571
```

El script agrega Firebase al proyecto de datos sin facturación, registra la aplicación web y habilita correo/contraseña. Primero acepta los términos desde Firebase Console si es la primera vez que usas el producto. Si Firebase pide inicializar Authentication, abre su consola, selecciona el proyecto y usa Authentication → Get started. No es necesario activar métodos sociales ni actualizar a Identity Platform. Luego repite el script. Si una pantalla propone Blaze, detente: se seleccionó un proyecto con facturación, no el proyecto Spark previsto.

Publica `firestore.rules` desde Firebase Console → Firestore → Rules para denegar acceso directo de clientes. Esta aplicación utiliza IAM desde el backend; no depende de reglas que permitan leer o escribir desde el navegador. El bucket regular de Cloud Storage se crea con prevención de acceso público y acceso uniforme.

## Gemini gratuito y secretos

Usa una clave de Google AI Studio de un proyecto que muestre **Free tier**, sin vincular facturación al proyecto de IA. Es independiente del proyecto que ejecuta Cloud Run. Mantén la clave en `.local/gemini-api-key.txt` y revisa que no tenga contenido adicional. No la pegues en el código, comandos públicos o README. El despliegue la copia a Secret Manager y el contenedor recibe una versión fija mediante `GOOGLE_API_KEY`.

`gemini-3.5-flash-lite` es el valor inicial, validado con el proyecto gratuito disponible en esta cuenta. El modelo se puede cambiar con `-GeminiModel`. ADK necesita tres llamadas por PQR; una respuesta de cuota agotada debe quedar como error y permitir reintento, sin cambiar automáticamente a un modelo de pago.

## Construir y desplegar

Ejecuta primero las pruebas y la compilación del README. Después:

```powershell
& .\scripts\deploy.ps1 -TrialConfirmed
```

Cloud Run construye cada Dockerfile con Cloud Build y almacena las imágenes en Artifact Registry. No necesitas Docker Desktop local. El script detiene la ejecución ante errores de comandos cloud y guarda las URLs en `.local/deployment.json`.

La cuenta que despliega necesita permisos de creación de los recursos y asignación de los roles que aparecen en el script. La identidad de compilación predeterminada recibe `roles/run.builder`. Si una política de organización impide exponer la interfaz públicamente, mantén la restricción y revisa una alternativa de acceso; no la desactives para superar el error.

## Validar la entrega

1. Abre la URL del frontend. `GET /api/health` debe indicar `mode=cloud` y `ai_mode=gemini`.
2. Registra una cuenta ficticia desde la interfaz. Crea una PQR de texto y otra con `samples/reclamo-ficticio.pdf`.
3. Verifica que el resultado declare `engine=google-adk`, que haya registros del propietario en Firestore y que el documento exista en el bucket privado.
4. Con otra cuenta ficticia, verifica que no pueda consultar o descargar la primera solicitud.
5. Una petición sin identidad IAM directamente a la API debe recibir 403. Las rutas privadas a través del frontend sin sesión deben recibir 401.
6. Revisa los registros cloud ante un error. No imprimas secretos, contraseñas ni el texto completo de las PQR en logs.

## GitHub y CI

Repositorio privado: `Juanariasp/pqr-demo`. El workflow `.github/workflows/ci.yml` ejecuta Ruff/pytest en Python 3.12 y `npm run build` en Node.js 22. Las credenciales cloud no están en GitHub y los pushes no despliegan automáticamente. El despliegue se mantiene explícito para controlar el consumo de la prueba.

## Recuperación y retiro

Cloud Run conserva revisiones. Para revertir, dirige el tráfico a una revisión verificada anterior con `gcloud run services update-traffic`. No borres Firestore o Storage durante una reversión del código. Para retirar la demo, revisa primero qué datos y recursos quieres conservar y luego elimina los dos servicios, imágenes de Artifact Registry, bucket y secreto. El borrado de datos debe ser una decisión explícita.

Las cargas abandonadas se limpian al realizar otra carga desde la misma cuenta. Una tarea global de limpieza permanece como mejora futura. Las copias del secreto y la sesión de la CLI quedan en `.local`; elimínalas o revoca el acceso al finalizar si ya no lo necesitas.
