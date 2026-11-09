"""Small JSON repository: SQLite locally, Firestore in Cloud Run.

Conditional updates protect upload ownership and processing against races.
"""

import json
import sqlite3
from datetime import UTC, datetime

from .config import settings


def now():
    return datetime.now(UTC).isoformat()


class LocalStore:
    def __init__(self):
        cfg = settings()
        cfg.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = cfg.data_dir / "pqr.sqlite3"
        with self.connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS records (collection TEXT, id TEXT, body TEXT, PRIMARY KEY(collection,id))"
            )

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def get(self, collection, key):
        with self.connect() as conn:
            row = conn.execute(
                "SELECT body FROM records WHERE collection=? AND id=?", (collection, key)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, collection, key, body):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO records VALUES (?,?,?) ON CONFLICT(collection,id) DO UPDATE SET body=excluded.body",
                (collection, key, json.dumps(body)),
            )

    def list(self, collection, owner):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT body FROM records WHERE collection=? AND json_extract(body, '$.owner')=?",
                (collection, owner),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def mutate(self, collection, key, fn):
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT body FROM records WHERE collection=? AND id=?", (collection, key)
            ).fetchone()
            body = fn(json.loads(row[0]) if row else None)
            conn.execute(
                "INSERT INTO records VALUES (?,?,?) ON CONFLICT(collection,id) DO UPDATE SET body=excluded.body",
                (collection, key, json.dumps(body)),
            )
        return body


class FirestoreStore:
    def __init__(self):
        from google.cloud import firestore

        self.client = firestore.Client(
            project=settings().firebase_project_id or settings().google_cloud_project
        )

    def get(self, collection, key):
        return self.client.collection(collection).document(key).get().to_dict()

    def put(self, collection, key, body):
        self.client.collection(collection).document(key).set(body)

    def list(self, collection, owner):
        from google.cloud.firestore_v1.base_query import FieldFilter

        return [
            doc.to_dict()
            for doc in self.client.collection(collection)
            .where(filter=FieldFilter("owner", "==", owner))
            .stream()
        ]

    def mutate(self, collection, key, fn):
        from google.cloud import firestore

        ref = self.client.collection(collection).document(key)

        @firestore.transactional
        def run(tx):
            body = fn(ref.get(transaction=tx).to_dict())
            tx.set(ref, body)
            return body

        return run(self.client.transaction())


class Files:
    def __init__(self):
        cfg = settings()
        self.cloud = cfg.app_mode == "cloud"
        if self.cloud:
            from google.cloud import storage

            self.bucket = storage.Client(project=cfg.google_cloud_project).bucket(
                cfg.storage_bucket
            )
        else:
            self.root = cfg.data_dir / "files"
            self.root.mkdir(parents=True, exist_ok=True)

    def save(self, key, data, mime):
        if self.cloud:
            self.bucket.blob(key).upload_from_string(data, content_type=mime)
        else:
            path = self.root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def read(self, key):
        if self.cloud:
            return self.bucket.blob(key).download_as_bytes()
        return (self.root / key).read_bytes()

    def delete(self, key):
        if self.cloud:
            from google.api_core.exceptions import NotFound

            try:
                self.bucket.blob(key).delete()
            except NotFound:
                pass
        else:
            (self.root / key).unlink(missing_ok=True)
