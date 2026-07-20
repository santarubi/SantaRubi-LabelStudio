"""Gerenciador simples de configurações para o Santa Rubi Label Studio.

Este módulo usa um arquivo JSON em data/config.json para salvar as
preferências do usuário sem precisar de banco de dados.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigManager:
    CONFIG_FILE = Path(__file__).resolve().parents[1] / "data" / "config.json"

    def __init__(self) -> None:
        self.config_file = self.CONFIG_FILE
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.config_file.exists():
            return {}

        try:
            text = self.config_file.read_text(encoding="utf-8")
            return json.loads(text)
        except Exception:
            return {}

    def save(self, config: dict[str, Any]) -> None:
        try:
            self.config_file.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
