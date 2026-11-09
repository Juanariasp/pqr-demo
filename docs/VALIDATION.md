# Evidencia de verificación

Fecha de ejecución: 8 de noviembre de 2026, zona America/Bogota.

## Verificación local

- 12 pruebas del backend aprobadas: autenticación, flujo completo de texto, archivos, propiedad por usuario, errores y reintento.
- Ruff aprobó el backend y sus pruebas.
- Next.js compiló correctamente con TypeScript estricto.
- Se probó desde el navegador el inicio de sesión, creación de PQR de texto, carga de Word, vista previa editable, conservación del texto original y consulta del resultado.
- El PDF ficticio se renderizó y se inspeccionó visualmente. El Word se abrió en Microsoft Word para revisión; el renderizador automatizado no estaba disponible porque faltaba LibreOffice.
- La llamada real a ADK ejecutó clasificador, analista y redactor con `gemini-3.5-flash-lite`. El modelo anterior devolvió 404 para esta cuenta y se sustituyó por el modelo gratuito disponible.

## GitHub e imágenes

- Repositorio privado: https://github.com/Juanariasp/pqr-demo
- Primera ejecución de CI aprobada: https://github.com/Juanariasp/pqr-demo/actions/runs/42537946727
- Construcción backend en Cloud Build: `bee37c78-08dd-449e-86c6-dab3c3038a23`, estado SUCCESS.
- Construcción frontend en Cloud Build: `227e05c3-92ea-447b-aeb9-6a3c7bf89ff0`, estado SUCCESS.

## Configuración desplegada

- Frontend público: https://pqr-web-53950210571.us-central1.run.app
- Backend privado: https://pqr-api-53950210571.us-central1.run.app
- `GET /api/health` del frontend respondió 200 e indicó `mode=cloud`, `ai_mode=gemini`.
- Registro real en Firebase y creación de una PQR de texto desde la interfaz pública: completados con respuesta de Google ADK.
- `scripts/smoke-cloud.py` aprobó el flujo integrado con dos cuentas ficticias: extracción de PDF y Word, edición del texto, persistencia en Firestore, análisis real, descarga idéntica al original por SHA-256 y rechazo del PDF escaneado con 422.
- Una segunda cuenta no pudo consultar, analizar ni descargar la PQR de la primera: 404 en las cuatro rutas comprobadas.
- La cookie de sesión del despliegue incluyó HttpOnly y Secure.
- `GET /api/pqrs` sin sesión respondió 401.
- Acceso directo al backend sin identidad IAM: 403.
- Acceso directo a Firestore sin autenticación: 403.
- El único invocador IAM explícito del backend es la cuenta de servicio `pqr-web`.
- Reglas Firestore publicadas: acceso directo de clientes denegado. El backend usa IAM.
- Firebase y Gemini se comprobaron con `billingEnabled=false` en sus respectivos proyectos.
- La consola de la cuenta de ejecución mostró Free trial, crédito disponible y finalización el 7 de febrero de 2027, sin cobro automático mientras no se actualice a una cuenta de pago. No se confirmó Blaze en el proyecto de ejecución ni se actualizó la cuenta de facturación.
