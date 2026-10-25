"""Santa Rubi Launcher — ferramenta de desenvolvimento.

Verifica se o código-fonte mudou desde o último build bem-sucedido. Se
não mudou, abre o Santa Rubi Label Studio.exe já existente direto. Se
mudou, roda scripts/build.bat automaticamente, espera terminar, e só
então abre o executável novo — ou mostra o log de erro, se o build falhar.

Apenas para desenvolvimento: não faz download de nenhuma atualização, só
automatiza a recompilação local (o que scripts/build.bat já fazia
manualmente).
"""

from __future__ import annotations

import subprocess
import sys
import threading
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

# Quando empacotado pelo PyInstaller, __file__ aponta para a pasta
# temporária de extração (_MEIxxxxxx), não para o projeto real — o
# Launcher precisa da pasta onde o .exe de fato está (dist/, um nível
# abaixo da raiz do projeto) para funcionar quando congelado.
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent.parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_runner import BuildResult, run_build
from scripts.project_signature import (
    compute_signature,
    current_git_version,
    load_build_info,
    needs_rebuild,
    save_build_info,
)
from ui.branding import APP_VERSION, apply_window_icon

BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build.bat"
EXE_PATH = PROJECT_ROOT / "dist" / "Santa Rubi Label Studio.exe"
BUILD_INFO_PATH = PROJECT_ROOT / "dist" / "build_info.json"


class LauncherWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Santa Rubi Launcher {APP_VERSION}")
        apply_window_icon(self)
        self.geometry("620x420")
        self.minsize(620, 420)

        self.status_var = tk.StringVar(value="Verificando alterações no projeto...")
        self.version_var = tk.StringVar(value=f"Versão atual: {current_git_version(PROJECT_ROOT)}")
        self.last_build_var = tk.StringVar(value="Último build: —")
        self.duration_var = tk.StringVar(value="Tempo de compilação: —")

        self._log_text: tk.Text | None = None

        self._build_widgets()
        self._refresh_build_info_labels()
        self.after(150, self._start)

    def _build_widgets(self) -> None:
        container = ttk.Frame(self, padding=16)
        container.pack(fill="both", expand=True)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(4, weight=1)

        ttk.Label(container, text="Santa Rubi Launcher", font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        info_frame = ttk.Frame(container)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(info_frame, textvariable=self.version_var).pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.last_build_var).pack(anchor="w")
        ttk.Label(info_frame, textvariable=self.duration_var).pack(anchor="w")

        ttk.Label(container, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 8)
        )

        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        self.log_frame = ttk.Frame(container)
        self.log_frame.grid(row=4, column=0, sticky="nsew")
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_remove()  # só aparece se o build falhar

        self._log_text = tk.Text(self.log_frame, height=12, wrap="word", state="disabled")
        self._log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(self.log_frame, orient="vertical", command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.grid(row=0, column=1, sticky="ns")

        self.button_row = ttk.Frame(container)
        self.button_row.grid(row=5, column=0, sticky="e", pady=(8, 0))
        self.copy_button = ttk.Button(self.button_row, text="Copiar erro", command=self._copy_log)
        self.close_button = ttk.Button(self.button_row, text="Fechar", command=self.destroy)

    def _refresh_build_info_labels(self) -> None:
        info = load_build_info(BUILD_INFO_PATH)
        if info is None:
            self.last_build_var.set("Último build: nunca")
            self.duration_var.set("Tempo de compilação: —")
            return

        self.last_build_var.set(f"Último build: {info.get('built_at', '—')}")
        duration = info.get("duration_seconds")
        if isinstance(duration, (int, float)):
            self.duration_var.set(f"Tempo de compilação: {duration:.1f}s")
        else:
            self.duration_var.set("Tempo de compilação: —")

    def _start(self) -> None:
        # console=False esconde qualquer exceção não tratada (a janela
        # simplesmente fica parada, sem nenhuma mensagem) — por isso todo
        # o fluxo de decisão fica protegido e mostra o erro no log em vez
        # de travar silenciosamente.
        try:
            info = load_build_info(BUILD_INFO_PATH)
            signature = compute_signature(PROJECT_ROOT)

            if not needs_rebuild(info, signature, EXE_PATH):
                self.status_var.set("Nenhuma alteração detectada. Abrindo o programa...")
                self.after(300, self._launch_app_and_close)
                return

            self.status_var.set("Projeto alterado desde o último build. Recompilando (build.bat)...")
            self.progress.start(12)
            threading.Thread(target=self._run_build_in_background, args=(signature,), daemon=True).start()
        except Exception:
            self.status_var.set("Erro inesperado no Launcher. Veja o log abaixo.")
            self._show_log(traceback.format_exc())

    def _run_build_in_background(self, signature: str) -> None:
        # Roda numa thread separada — uma exceção aqui não aciona o
        # report_callback_exception do Tk nem aparece em lugar nenhum
        # (console=False), então também precisa ser capturada.
        try:
            result = run_build(BUILD_SCRIPT, PROJECT_ROOT)
        except Exception:
            error_log = traceback.format_exc()
            self.after(0, lambda: self._on_build_crashed(error_log))
            return
        self.after(0, lambda: self._on_build_finished(result, signature))

    def _on_build_crashed(self, error_log: str) -> None:
        self.progress.stop()
        self.status_var.set("Erro inesperado ao rodar o build. Veja o log abaixo.")
        self._show_log(error_log)

    def _on_build_finished(self, result: BuildResult, signature: str) -> None:
        self.progress.stop()
        success = result.success and EXE_PATH.exists()

        if success:
            info = {
                "version": current_git_version(PROJECT_ROOT),
                "built_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "duration_seconds": round(result.duration_seconds, 1),
                "signature": signature,
            }
            save_build_info(BUILD_INFO_PATH, info)
            self._refresh_build_info_labels()
            self.status_var.set(f"Build concluído em {result.duration_seconds:.1f}s. Abrindo o programa...")
            self.after(500, self._launch_app_and_close)
        else:
            self.status_var.set("Falha no build — o programa NÃO foi aberto. Veja o log abaixo.")
            self._show_log(result.log)

    def _show_log(self, log: str) -> None:
        self.log_frame.grid()
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", tk.END)
        self._log_text.insert("1.0", log or "(build.bat não produziu saída)")
        self._log_text.configure(state="disabled")
        self.copy_button.pack(side="left", padx=(0, 8))
        self.close_button.pack(side="left")

    def _copy_log(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._log_text.get("1.0", tk.END))

    def _launch_app_and_close(self) -> None:
        try:
            subprocess.Popen([str(EXE_PATH)], cwd=PROJECT_ROOT)
        finally:
            self.destroy()


def main() -> None:
    LauncherWindow().mainloop()


if __name__ == "__main__":
    main()
