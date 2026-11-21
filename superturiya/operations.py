"""Local SQLite backup and restore to a new path. Existing files are never replaced."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path

from .models import utc_now


def database(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ValueError("source database does not exist")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("source database integrity check failed")
        if not connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traces'").fetchone():
            raise ValueError("source is not a SuperTuriya database")
    except Exception:
        connection.close()
        raise
    return connection


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def snapshot(source_path: str, output_path: str) -> dict:
    source, output = Path(source_path), Path(output_path)
    connection = database(source)
    created = False
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        created = True
        target = sqlite3.connect(output)
        try:
            connection.backup(target)
            if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("backup integrity check failed")
        finally:
            target.close()
        return {"schema": "superturiya-backup-v1", "created_at": utc_now(), "sha256": digest(output), "bytes": output.stat().st_size}
    except Exception:
        if created:
            output.unlink(missing_ok=True)
        raise
    finally:
        connection.close()


def restore(source_path: str, manifest_path: str, output_path: str) -> dict:
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get("schema") != "superturiya-backup-v1" or digest(Path(source_path)) != manifest.get("sha256"):
        raise ValueError("backup manifest or content digest does not match")
    return snapshot(source_path, output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    backup = sub.add_parser("backup")
    backup.add_argument("--db", required=True)
    backup.add_argument("--output", required=True)
    recover = sub.add_parser("restore")
    recover.add_argument("--backup", required=True)
    recover.add_argument("--manifest", required=True)
    recover.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            manifest_path = Path(args.output + ".manifest.json")
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            with manifest_path.open("x") as output:
                try:
                    receipt = snapshot(args.db, args.output)
                    json.dump(receipt, output, indent=2)
                except Exception:
                    manifest_path.unlink(missing_ok=True)
                    raise
        else:
            receipt = restore(args.backup, args.manifest, args.output)
        print(json.dumps(receipt, indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__": main()
