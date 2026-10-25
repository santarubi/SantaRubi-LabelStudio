@echo off
title Santa Rubi Label Studio - Release Build

cd /d "%~dp0.."
python scripts\build_release.py %*

if errorlevel 1 (
    echo.
    echo BUILD RELEASE FALHOU.
    pause
    exit /b 1
)

echo.
echo RELEASE concluida em release\
pause
