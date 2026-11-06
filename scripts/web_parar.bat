@echo off
REM Encerra o Airline Manager 4 Bot (modo web ou desktop) e fecha tambem o Chrome.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0web_parar.ps1" %*
