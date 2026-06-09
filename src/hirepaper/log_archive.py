from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any


class LogArchiveError(Exception):
    pass


class StagedLogArchive:
    def __init__(self, destination: str | Path, prefix: str = "hirepaper-log-") -> None:
        self.destination = Path(destination)
        self.prefix = prefix
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None
        self._finalized = False

    def __enter__(self) -> "StagedLogArchive":
        self._tmp = tempfile.TemporaryDirectory(prefix=self.prefix)
        self.root = Path(self._tmp.name)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.cleanup()

    def _require_root(self) -> Path:
        if self.root is None:
            raise LogArchiveError("log archive staging directory is not initialized")
        return self.root

    def _target(self, relative_path: str | Path) -> Path:
        root = self._require_root()
        rel = Path(relative_path)
        if rel.is_absolute():
            raise LogArchiveError(f"archive member path must be relative: {relative_path}")
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def write_text(self, relative_path: str | Path, content: str, encoding: str = "utf-8") -> None:
        self._target(relative_path).write_text(content, encoding=encoding)

    def write_json(self, relative_path: str | Path, data: Any) -> None:
        self.write_text(relative_path, json.dumps(data, indent=2, ensure_ascii=False))

    def copy_file(self, src: str | Path, relative_path: str | Path | None = None) -> bool:
        source = Path(src)
        if not source.exists():
            return False
        target = self._target(relative_path or source.name)
        shutil.copy2(source, target)
        return True

    def list_members(self) -> list[str]:
        root = self._require_root()
        members: list[str] = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                members.append(path.relative_to(root).as_posix())
        return members

    def finalize(self) -> Path:
        if self._finalized:
            return self.destination

        root = self._require_root()
        try:
            self.destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise LogArchiveError(f"cannot create log archive parent directory: {self.destination.parent} — {e}")

        try:
            with zipfile.ZipFile(self.destination, "w", zipfile.ZIP_DEFLATED) as zf:
                for path in sorted(root.rglob("*")):
                    if path.is_file():
                        zf.write(path, path.relative_to(root).as_posix())
        except OSError as e:
            raise LogArchiveError(f"cannot create log archive: {self.destination} — {e}")

        self._finalized = True
        return self.destination

    def cleanup(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None
            self.root = None
