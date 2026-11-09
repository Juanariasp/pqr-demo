"""Publish the demo's deny-all client rules; backend access uses IAM."""

import argparse
import os
import subprocess
from pathlib import Path

import httpx

parser = argparse.ArgumentParser()
parser.add_argument("--project", default="pqr-demo-data-53950210571")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
sdk = root / ".tools/google-cloud-sdk/bin/gcloud.cmd"
if sdk.exists():
    os.environ["CLOUDSDK_CONFIG"] = str(root / ".local/gcloud")
    os.environ["CLOUDSDK_PYTHON"] = str(root / "backend/.venv/Scripts/python.exe")
else:
    sdk = "gcloud"
token = subprocess.check_output([str(sdk), "auth", "print-access-token"], text=True).strip()
base = f"https://firebaserules.googleapis.com/v1/projects/{args.project}"
with httpx.Client(
    headers={"Authorization": f"Bearer {token}", "x-goog-user-project": args.project}, timeout=30
) as client:
    response = client.post(
        f"{base}/rulesets",
        json={
            "source": {
                "files": [
                    {"name": "firestore.rules", "content": (root / "firestore.rules").read_text()}
                ]
            }
        },
    )
    if response.is_error:
        raise SystemExit(
            f"Rules API HTTP {response.status_code}: {response.json().get('error', {}).get('message', 'Error remoto')}"
        )
    release = {
        "name": f"projects/{args.project}/releases/cloud.firestore",
        "rulesetName": response.json()["name"],
    }
    existing = client.get(f"{base}/releases/cloud.firestore")
    if existing.status_code == 404:
        response = client.post(f"{base}/releases", json=release)
    else:
        existing.raise_for_status()
        response = client.patch(
            f"{base}/releases/cloud.firestore",
            json={"release": release, "updateMask": "rulesetName"},
        )
    response.raise_for_status()
print("Firestore: acceso directo de clientes denegado. El backend conserva su acceso por IAM.")
