"""Create fictitious examples on localhost only. Run with backend/.venv Python."""

import sys

import httpx

base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
if not base.startswith(("http://127.0.0.1:", "http://localhost:")):
    raise SystemExit("Este script solo acepta localhost.")
credentials = {"email": "demo@nexo.test", "password": "NexoDemo2026!"}
samples = [
    (
        "Revisión de cobro duplicado",
        "Solicito revisar un cobro duplicado de $45.000 en mi factura FAC-DEMO-001 del 2026-11-01. El servicio corresponde a una cuenta ficticia. Espero conocer el origen del cargo y solicitar su corrección si corresponde.",
    ),
    (
        "Información sobre mi plan de servicio",
        "Solicito información acerca de las características y condiciones del plan de servicio asociado a la referencia REF-DEMO-002. Quisiera conocer las opciones disponibles para realizar un cambio. Todos los datos son ficticios.",
    ),
    (
        "Inconformidad con la atención recibida",
        "Presento una queja por la mala atención que recibí en una llamada de soporte relacionada con el CASO-DEMO-003. No obtuve una explicación clara sobre el seguimiento del incidente. Solicito que se revise la calidad de la atención.",
    ),
]
with httpx.Client(base_url=base, timeout=110) as client:
    if client.get("/health").json()["mode"] != "local":
        raise SystemExit("La carga de datos de ensayo está deshabilitada en cloud.")
    auth = client.post("/auth/register", json=credentials)
    if auth.status_code != 201:
        auth = client.post("/auth/login", json=credentials)
    auth.raise_for_status()
    client.headers["Authorization"] = f"Bearer {auth.json()['token']}"
    existing = {pqr["title"] for pqr in client.get("/pqrs").json()}
    for title, text in samples:
        if title in existing:
            continue
        response = client.post("/pqrs", json={"title": title, "text": text})
        response.raise_for_status()
        key = response.json()["id"]
        output = client.post(f"/pqrs/{key}/analyze")
        output.raise_for_status()
        print(output.json()["reference"], output.json()["status"])
print("Cuenta local ficticia: demo@nexo.test / NexoDemo2026!")
