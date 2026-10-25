"""Metadados e validações compartilhados pelo build de produção.

Não importa módulos da aplicação nem lê configurações do usuário. Isso mantém
o pipeline de release independente de ``%LOCALAPPDATA%`` e de qualquer segredo.
"""

from __future__ import annotations

import hashlib
import runpy
from datetime import datetime
from pathlib import Path
from typing import Any

PRODUCT_NAME = "Santa Rubi Label Studio"
COMPANY_NAME = "Santa Rubi Semijoias"
COPYRIGHT = "© 2026 Santa Rubi Semijoias"
EXECUTABLE_NAME = f"{PRODUCT_NAME}.exe"


def load_version(project_root: Path) -> dict[str, Any]:
    """Carrega a fonte única de versão sem importar o restante da aplicação."""
    return runpy.run_path(str(project_root / "app" / "version.py"))


def render_windows_version_info(project_root: Path) -> str:
    version = load_version(project_root)
    version_tuple = tuple(version["WINDOWS_VERSION"])
    version_text = str(version["APP_VERSION"])

    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple!r},
    prodvers={version_tuple!r},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable('041604B0', [
        StringStruct('CompanyName', '{COMPANY_NAME}'),
        StringStruct('FileDescription', 'Sistema de impressão de etiquetas'),
        StringStruct('FileVersion', '{version_text}'),
        StringStruct('InternalName', '{PRODUCT_NAME}'),
        StringStruct('LegalCopyright', '{COPYRIGHT}'),
        StringStruct('OriginalFilename', '{EXECUTABLE_NAME}'),
        StringStruct('ProductName', '{PRODUCT_NAME}'),
        StringStruct('ProductVersion', '{version_text}'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1046, 1200])])
  ]
)
"""


def write_windows_version_info(project_root: Path, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_windows_version_info(project_root), encoding="utf-8")
    return destination


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def render_release_info(
    project_root: Path,
    executable: Path,
    *,
    build_time: datetime,
    signed: bool,
) -> str:
    version = load_version(project_root)
    return "\n".join(
        [
            f"Produto: {PRODUCT_NAME}",
            f"Versão: {version['APP_VERSION']}",
            f"Build: {build_time.astimezone().isoformat(timespec='seconds')}",
            f"Arquivo: {EXECUTABLE_NAME}",
            f"Tamanho: {executable.stat().st_size} bytes",
            f"SHA-256: {sha256_file(executable)}",
            "Arquitetura: Windows x64",
            f"Assinatura digital: {'Authenticode' if signed else 'Não assinado (NotSigned)'}",
            "",
            "Distribuição: copiar este arquivo EXE e o RELEASE_INFO.txt.",
            "O Launcher, o código-fonte e o ambiente Python não fazem parte da release.",
        ]
    ) + "\n"
