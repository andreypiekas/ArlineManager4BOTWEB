@echo off
REM Envia o codigo deste computador para o Raspberry e reinicia os bots (veja desplegar_pi.ps1).
title Airline Manager 4 Bot - implantar no Raspberry
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0desplegar_pi.ps1" %*
pause
