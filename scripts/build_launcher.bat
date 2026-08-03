@echo off
title Santa Rubi Launcher - Build

REM Vai para a pasta raiz do projeto
cd /d "%~dp0.."

echo.
echo =====================================
echo   Santa Rubi Launcher - Build
echo =====================================
echo.

echo Gerando executavel do Launcher...
REM Sem limpar build/dist antes: essas pastas sao compartilhadas com o
REM Santa Rubi Label Studio.exe e com o dist\build_info.json que o
REM proprio Launcher usa para saber quando foi o ultimo build. O
REM PyInstaller sobrescreve so os arquivos do Launcher (dist\Santa Rubi
REM Launcher.exe e build\Santa Rubi Launcher\) sem tocar no resto.
python -m PyInstaller "Santa Rubi Launcher.spec"

if errorlevel 1 (
    echo.
    echo =====================================
    echo         ERRO NO BUILD!
    echo =====================================
    pause
    exit /b 1
)

echo.
echo =====================================
echo     BUILD DO LAUNCHER CONCLUIDO!
echo =====================================
echo.
echo Executavel: dist\Santa Rubi Launcher.exe
pause
