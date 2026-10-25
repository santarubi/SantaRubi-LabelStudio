"""Versão oficial do produto.

Este é o único local editado manualmente quando uma nova versão é criada.
Os metadados do Windows e o relatório de release são gerados a partir daqui.
"""

VERSION = (1, 2, 0)
VERSION_TEXT = ".".join(str(part) for part in VERSION)
APP_VERSION = f"v{VERSION_TEXT}"
WINDOWS_VERSION = (*VERSION, 0)
