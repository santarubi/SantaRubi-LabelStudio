@echo off
title Santa Rubi Label Studio - Build

REM Vai para a pasta raiz do projeto
cd /d "%~dp0.."

echo.
echo =====================================
echo   Santa Rubi Label Studio - Build
echo =====================================
echo.

echo Limpando builds anteriores...
if exist build rmdir /S /Q build
if exist dist rmdir /S /Q dist

echo.
echo Gerando executavel...
python -m PyInstaller "Santa Rubi Label Studio.spec"

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
echo     BUILD CONCLUIDO COM SUCESSO!
echo =====================================

pause