# Santa Rubi Label Studio v1.1.2 — Release Build

Esta é a primeira distribuição formal destinada ao computador de produção.
Não altera regras de negócio, impressão, ZPL, layout físico, Excel ou API
Jueri.

## Fonte da versão

`app/version.py` é a fonte única editada manualmente. O branding, os metadados
do Windows e o `RELEASE_INFO.txt` recebem a versão a partir desse arquivo.

## Ambiente reproduzível

- Windows 10 ou 11 x64;
- Python 3.14.6 x64;
- dependências exatas de `requirements-release.txt`.

Preparação:

```bat
python -m pip install -r requirements-release.txt
```

Build:

```bat
scripts\build_release.bat
```

O pipeline usa o `Santa Rubi Label Studio.spec`, sempre com `upx=False`, e
publica somente:

```text
release/
    Santa Rubi Label Studio.exe
    RELEASE_INFO.txt
```

## Separação DEV e RELEASE

DEV:

- código-fonte, testes e documentação;
- `Santa Rubi Launcher.exe` e `scripts/launcher.py`;
- rebuild automático e `build_info.json`;
- Python, PyInstaller e demais ferramentas.

RELEASE:

- executável one-file do aplicativo;
- relatório de integridade;
- sem Launcher, código-fonte, Python, testes, logs ou configuração pessoal.

O novo usuário recebe configurações em
`%LOCALAPPDATA%\Santa Rubi Label Studio\`. Nenhum `config.json` é levado no
pacote.

## Assinatura Authenticode

O ponto oficial de assinatura fica depois da geração/validação do EXE e antes
do cálculo do SHA-256. Enquanto não houver certificado legítimo, o build padrão
permanece `NotSigned`.

Quando houver certificado, executar diretamente o script com os três valores
reais, sem armazená-los no repositório:

```bat
python scripts\build_release.py ^
  --signtool "CAMINHO_REAL\signtool.exe" ^
  --certificate-thumbprint "THUMBPRINT_REAL" ^
  --timestamp-url "URL_REAL_DO_SERVIDOR_DE_TIMESTAMP"
```

O script chama `signtool sign`, valida com `signtool verify`, e somente então
calcula o hash e gera o relatório.

## Smoke test isolado

Após o build, a inicialização sem o código-fonte pode ser validada sem usar a
configuração operacional do usuário:

```bat
python scripts\smoke_release.py
```

O verificador copia temporariamente o EXE, usa `LOCALAPPDATA` e `TEMP`
isolados, confirma que o processo permanece ativo e encerra toda a árvore por
um Job Object do Windows. Nenhuma impressão é disparada.

## Instalação no computador de produção

Copiar apenas os dois arquivos de `release/`. O EXE não depende do Launcher,
do repositório, de Python, de `requirements.txt` nem de uma pasta `assets/`.
A planilha e o driver da ELGIN L42 PRO FULL são recursos operacionais externos
e devem ser configurados no computador de destino.
