@echo off
rem Doble clic para iniciar AutoServicio Demo (datos ficticios).
rem Prepara lo necesario la primera vez, libera el puerto y abre el navegador.
title AutoServicio Demo
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" %*
