"""Configure Firebase through its official Management and Auth APIs.

Run only after reviewing cloud permissions. Uses gcloud's existing OAuth session;
it never prints tokens, passwords or API keys.
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--project", required=True)
parser.add_argument("--runtime-project", default="project-2e2f3efa-3e25-45e6-b44")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
sdk = root / ".tools/google-cloud-sdk/bin/gcloud.cmd"
if sdk.exists():
    os.environ["CLOUDSDK_CONFIG"] = str(root / ".local/gcloud")
    os.environ["CLOUDSDK_PYTHON"] = str(root / "backend/.venv/Scripts/python.exe")
else:
    sdk = "gcloud"
token = subprocess.check_output(
    [str(sdk), "auth", "print-access-token"], text=True
).strip()
client = httpx.Client(
    headers={"Authorization": f"Bearer {token}", "x-goog-user-project": args.project},
    timeout=60,
)
base = "https://firebase.googleapis.com/v1beta1"


def checked(response):
    if response.is_error:
        try:
            message = response.json().get("error", {}).get("message", "Error remoto")
        except ValueError:
            message = "Error remoto"
        raise SystemExit(
            f"{response.request.method} {response.request.url.path}: HTTP {response.status_code}: {message}"
        )
    return response.json() if response.content else {}


def operation(data):
    if "name" not in data or not data["name"].startswith("operations/"):
        return data
    for _ in range(120):
        state = checked(client.get(f"{base}/{data['name']}"))
        if state.get("done"):
            if state.get("error"):
                raise SystemExit(state["error"]["message"])
            return state.get("response", {})
        time.sleep(2)
    raise SystemExit("Firebase aún se está configurando; vuelve a ejecutar el script.")


project = f"projects/{args.project}"
existing = client.get(f"{base}/{project}")
if existing.status_code == 404:
    operation(checked(client.post(f"{base}/{project}:addFirebase", json={})))
else:
    checked(existing)
apps = checked(client.get(f"{base}/{project}/webApps")).get("apps", [])
web = next((app for app in apps if app.get("displayName") == "Nexo PQR web"), None)
if not web:
    web = operation(
        checked(
            client.post(
                f"{base}/{project}/webApps", json={"displayName": "Nexo PQR web"}
            )
        )
    )
config = checked(client.get(f"{base}/{project}/webApps/{web['appId']}/config"))
output = {
    "project_id": args.runtime_project,
    "firebase_project_id": args.project,
    "firebase_web_api_key": config["apiKey"],
    "firebase_app_id": web["appId"],
    "storage_bucket": f"{args.runtime_project}-pqr-files",
}
target = root / ".local/cloud-config.json"
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(output, indent=2), encoding="utf-8")
auth_url = f"https://identitytoolkit.googleapis.com/admin/v2/{project}/config"
response = client.patch(
    auth_url,
    params={"updateMask": "signIn.email.enabled,signIn.email.passwordRequired"},
    json={"signIn": {"email": {"enabled": True, "passwordRequired": True}}},
)
if response.status_code in (400, 404) and "CONFIGURATION_NOT_FOUND" in response.text:
    raise SystemExit(
        "Firebase fue agregado. Abre Firebase Console > Authentication > Get started; luego vuelve a ejecutar este script. No es necesario actualizar a Identity Platform."
    )
checked(response)
print(
    "Firebase configurado: autenticación con correo/contraseña y aplicación web. Configuración guardada en .local/cloud-config.json."
)
