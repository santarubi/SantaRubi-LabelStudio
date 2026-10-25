"""Gera o pacote formal de produção em ``release/``.

Pipeline: valida ambiente -> PyInstaller -> valida conteúdo -> assinatura
Authenticode opcional -> hash/relatório -> publicação em ``release/``.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import shutil
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pefile
from PyInstaller.archive.readers import CArchiveReader

from scripts.release_metadata import (
    EXECUTABLE_NAME,
    PRODUCT_NAME,
    load_version,
    render_release_info,
)

SPEC_FILE = PROJECT_ROOT / f"{PRODUCT_NAME}.spec"
RELEASE_ROOT = PROJECT_ROOT / "release"
RELEASE_DIR = RELEASE_ROOT / str(load_version(PROJECT_ROOT)["APP_VERSION"])
BUILD_ROOT = PROJECT_ROOT / "build" / "release"
STAGING_DIR = BUILD_ROOT / "dist"
WORK_DIR = BUILD_ROOT / "work"

EXPECTED_PYTHON = (3, 14, 6)
EXPECTED_PACKAGES = {
    "PyInstaller": "6.21.0",
    "altgraph": "0.17.5",
    "packaging": "26.2",
    "pefile": "2024.8.26",
    "pyinstaller-hooks-contrib": "2026.6",
    "pywin32-ctypes": "0.2.3",
    "setuptools": "83.0.0",
    "openpyxl": "3.1.5",
    "et_xmlfile": "2.0.0",
    "Pillow": "12.3.0",
    "pywin32": "312",
}

FORBIDDEN_ARCHIVE_NAMES = {
    "build_info.json",
    "config.json",
    "jueri_debug.log",
    "print_log.txt",
    "santa rubi launcher.exe",
}


def validate_build_environment() -> None:
    if sys.platform != "win32":
        app_version = str(load_version(PROJECT_ROOT)["APP_VERSION"])
        raise RuntimeError(f"O build RELEASE {app_version} deve ser executado no Windows.")
    if tuple(sys.version_info[:3]) != EXPECTED_PYTHON:
        expected = ".".join(map(str, EXPECTED_PYTHON))
        actual = platform.python_version()
        raise RuntimeError(f"Python incorreto: esperado {expected}; encontrado {actual}.")
    if struct.calcsize("P") * 8 != 64:
        raise RuntimeError("O build RELEASE deve usar Python de 64 bits.")

    mismatches: list[str] = []
    for package, expected in EXPECTED_PACKAGES.items():
        try:
            actual = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            actual = "não instalado"
        if actual != expected:
            mismatches.append(f"{package}: esperado {expected}; encontrado {actual}")
    if mismatches:
        raise RuntimeError("Dependências de build divergentes:\n- " + "\n- ".join(mismatches))


def reset_output_directory(path: Path, expected_parent: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != expected_parent.resolve():
        raise RuntimeError(f"Diretório de saída inesperado: {resolved}")
    if resolved.exists():
        shutil.rmtree(resolved)
    resolved.mkdir(parents=True, exist_ok=True)


def run_pyinstaller() -> Path:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(STAGING_DIR),
        "--workpath",
        str(WORK_DIR),
        str(SPEC_FILE),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)
    executable = STAGING_DIR / EXECUTABLE_NAME
    if not executable.is_file():
        raise RuntimeError(f"PyInstaller não gerou o executável esperado: {executable}")
    return executable


def archive_names(executable: Path) -> set[str]:
    return {name.replace("\\", "/").lower() for name in CArchiveReader(str(executable)).toc}


def validate_archive(executable: Path) -> None:
    names = archive_names(executable)
    basenames = {Path(name).name for name in names}
    forbidden = sorted(FORBIDDEN_ARCHIVE_NAMES & basenames)
    if forbidden:
        raise RuntimeError("Arquivos proibidos encontrados no EXE: " + ", ".join(forbidden))

    required = {
        "assets/santa-rubi-app.ico",
        f"python{sys.version_info.major}{sys.version_info.minor}.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll",
        "win32/win32print.pyd",
        "_tkinter.pyd",
    }
    missing = sorted(required - names)
    if missing:
        raise RuntimeError("Dependências ausentes no EXE: " + ", ".join(missing))

    if any(name.startswith("tests/") or "/tests/" in name for name in names):
        raise RuntimeError("O EXE contém arquivos de teste.")
    if any("santa rubi launcher" in name for name in names):
        raise RuntimeError("O EXE RELEASE contém o Launcher.")


def validate_pe(executable: Path, expected_version: str) -> None:
    pe = pefile.PE(str(executable), fast_load=False)
    try:
        if pe.FILE_HEADER.Machine != 0x8664:
            raise RuntimeError("O executável gerado não é Windows x64 (AMD64).")

        product_versions: list[str] = []
        for file_info_group in getattr(pe, "FileInfo", []):
            for file_info in file_info_group:
                if getattr(file_info, "Key", b"") != b"StringFileInfo":
                    continue
                for string_table in file_info.StringTable:
                    entries = {
                        key.decode(errors="replace"): value.decode(errors="replace")
                        for key, value in string_table.entries.items()
                    }
                    product_versions.append(entries.get("ProductVersion", ""))
        if expected_version not in product_versions:
            raise RuntimeError(
                f"ProductVersion incorreta: esperado {expected_version}; encontrado {product_versions}."
            )
    finally:
        pe.close()


def sign_with_authenticode(
    executable: Path,
    *,
    signtool: Path,
    certificate_thumbprint: str,
    timestamp_url: str,
) -> None:
    """Ponto oficial de assinatura: depois do build e antes do SHA-256."""
    command = [
        str(signtool),
        "sign",
        "/sha1",
        certificate_thumbprint,
        "/fd",
        "SHA256",
        "/tr",
        timestamp_url,
        "/td",
        "SHA256",
        str(executable),
    ]
    subprocess.run(command, check=True)
    subprocess.run([str(signtool), "verify", "/pa", str(executable)], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RELEASE do Santa Rubi Label Studio")
    parser.add_argument("--signtool", type=Path)
    parser.add_argument("--certificate-thumbprint")
    parser.add_argument("--timestamp-url")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    signing_values = (args.signtool, args.certificate_thumbprint, args.timestamp_url)
    if any(signing_values) and not all(signing_values):
        raise RuntimeError(
            "Para assinar, informe --signtool, --certificate-thumbprint e --timestamp-url juntos."
        )

    validate_build_environment()
    version = load_version(PROJECT_ROOT)

    reset_output_directory(BUILD_ROOT, PROJECT_ROOT / "build")
    reset_output_directory(RELEASE_DIR, RELEASE_ROOT)

    executable = run_pyinstaller()
    validate_archive(executable)
    validate_pe(executable, str(version["APP_VERSION"]))

    signed = bool(all(signing_values))
    if signed:
        sign_with_authenticode(
            executable,
            signtool=args.signtool,
            certificate_thumbprint=args.certificate_thumbprint,
            timestamp_url=args.timestamp_url,
        )

    release_executable = RELEASE_DIR / EXECUTABLE_NAME
    shutil.copy2(executable, release_executable)
    build_time = datetime.now().astimezone()
    release_info = render_release_info(
        PROJECT_ROOT,
        release_executable,
        build_time=build_time,
        signed=signed,
    )
    (RELEASE_DIR / "RELEASE_INFO.txt").write_text(release_info, encoding="utf-8")

    print(release_info, end="")
    print(f"Artefato: {release_executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
