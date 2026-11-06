@echo off
REM Abre o painel web do Airline Manager 4 Bot e, se nao estiver ativo, inicia o modo web
REM (sem janela) neste terminal. Para parar: scripts\web_parar.bat.
title Airline Manager 4 Bot web
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web.ps1" %*
