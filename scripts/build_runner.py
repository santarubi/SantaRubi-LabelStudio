"""Executa scripts/build.bat de forma não-interativa e captura o log.

Separado do launcher.py para poder ser testado sem abrir nenhuma janela
Tk — só depende de subprocess, que os testes mockam.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Só existe em builds Windows do Python — getattr com fallback evita
# AttributeError caso este módulo seja importado (ex.: só para rodar os
# testes) num ambiente não-Windows.
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class BuildResult:
    success: bool
    log: str
    duration_seconds: float


def run_build(
    build_script: Path,
    cwd: Path,
    on_output_line: Callable[[str], None] | None = None,
) -> BuildResult:
    """Roda build_script via `cmd /c`, capturando stdout+stderr linha a
    linha (repassados a on_output_line, se informado — o Launcher usa
    isso para atualizar a UI ao vivo durante o build).

    stdin=DEVNULL é essencial: build.bat termina com `pause`, que travaria
    esperando uma tecla para sempre se rodado sem console interativo. Com
    stdin fechado, `pause` recebe EOF e segue em frente imediatamente.

    creationflags=CREATE_NO_WINDOW evita que uma janela preta do Prompt de
    Comando apareça durante o build — o usuário só vê a interface do
    Launcher (barra de progresso + log), nunca o console do cmd/PyInstaller.
    """
    start = time.monotonic()
    lines: list[str] = []

    process = subprocess.Popen(
        ["cmd", "/c", str(build_script)],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=CREATE_NO_WINDOW,
    )

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")
        lines.append(line)
        if on_output_line is not None:
            on_output_line(line)

    process.wait()
    duration = time.monotonic() - start

    return BuildResult(success=(process.returncode == 0), log="\n".join(lines), duration_seconds=duration)
