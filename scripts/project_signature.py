"""Assinatura do estado do código-fonte, usada pelo Launcher (dev) para
decidir se precisa recompilar o projeto.

Puramente utilitário — sem Tkinter, sem subprocess de build — para poder
ser testado sem abrir nenhuma janela nem rodar o PyInstaller de verdade.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

TRACKED_EXTENSIONS = {".py", ".spec", ".txt"}
EXCLUDED_DIR_NAMES = {
    ".git",
    "__pycache__",
    "build",
    "dist",
    "venv",
    ".venv",
    "env",
    ".claude",
    ".vscode",
}


def _iter_tracked_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.relative_to(root).parts[:-1]):
            continue
        if path.suffix.lower() in TRACKED_EXTENSIONS:
            yield path


def compute_signature(root: Path) -> str:
    """SHA-256 sobre nome+conteúdo de todo .py/.spec/.txt do projeto,
    fora de build/dist/venv/.git/__pycache__ — muda sempre que qualquer
    um desses arquivos muda, tanto faz a ordem em que o filesystem os
    lista (a iteração é sempre em ordem alfabética de caminho)."""
    digest = hashlib.sha256()
    for path in _iter_tracked_files(root):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def needs_rebuild(build_info: dict[str, Any] | None, current_signature: str, exe_path: Path) -> bool:
    """True se o projeto precisa ser recompilado: nunca buildado, código
    mudou desde o último build bem-sucedido, ou o .exe não existe mais
    (ex.: último build falhou e apagou dist/)."""
    if build_info is None:
        return True
    if build_info.get("signature") != current_signature:
        return True
    if not exe_path.exists():
        return True
    return False


def load_build_info(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save_build_info(path: Path, info: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def current_git_version(root: Path) -> str:
    """Reaproveita as tags já usadas no projeto (v1.0-print-engine,
    v3.0-stable, ...) em vez de inventar um esquema de versão novo."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "desconhecida"

    version = result.stdout.strip()
    return version or "desconhecida"
