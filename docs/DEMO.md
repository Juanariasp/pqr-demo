# Guion de la entrevista

Duración sugerida: 7 minutos. Usa únicamente datos ficticios y abre la demo antes de iniciar, para evitar que el arranque en frío consuma tiempo de presentación.

1. Presenta el objetivo: un usuario puede registrar una PQR, aportar un documento, consultar su clasificación y revisar una respuesta sugerida. Aclara si estás usando la demo local por reglas o el despliegue real con Google ADK y Gemini.
2. Entra con una cuenta ficticia. Muestra el resumen y el historial. La cuenta `demo@nexo.test` existe solamente en local después de ejecutar `seed_demo.py`.
3. Crea una solicitud con `samples/reclamo-ficticio.docx`. Muestra que se extrae el texto; agrega una frase antes de enviar. En el detalle, compara el texto confirmado con el original del documento.
4. Explica la secuencia: recibido → en análisis → completado. Muestra categoría, prioridad, tema, datos extraídos y respuesta sugerida. La interfaz puede terminar rápido en modo local; los estados intermedios quedan guardados en el backend.
5. Abre `samples/escaneado-sin-texto.pdf`. Muestra el error específico y explica por qué OCR queda fuera del prototipo. También hay un Word vacío y un PDF corrupto para otros errores.
6. Explica el aislamiento: el token identifica al usuario; el backend consulta la propiedad de la solicitud y del documento. Un ID ajeno devuelve 404. Cloud Run exige además la identidad IAM del servicio frontend.
7. Muestra `/docs` local y la ejecución de las pruebas. Explica las limitaciones sin presentar la demo como un sistema de producción.

Preguntas que conviene anticipar:

- **¿Por qué tres agentes?** El flujo es pequeño y determinista. Cada agente tiene una responsabilidad, un esquema validado y una salida persistida al finalizar el coordinador. Se puede explicar y probar sin decisiones autónomas de enrutamiento.
- **¿Por qué no tareas en segundo plano?** Cloud Run puede retirar CPU o finalizar instancias después de responder. El análisis se completa dentro de una petición con timeout y reserva transaccional. Si se necesita volumen o más duración, la siguiente mejora es una cola durable.
- **¿Es gratis?** El modelo puede usar el nivel gratuito de Gemini con sus cuotas. La infraestructura tiene cobros separados; no se promete costo cero.
- **¿La respuesta resuelve la PQR?** No. Es una sugerencia que requiere revisión humana y no inventa acciones ejecutadas, promesas o plazos.
- **¿Qué cambiarías primero?** Limpieza programada, renovación de sesión, verificación de correo, límites por usuario y pruebas integradas contra los servicios cloud.
