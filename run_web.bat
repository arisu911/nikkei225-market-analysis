@echo off
title Nikkei 225 Market Behavior Research Web (FastAPI)
cd /d "%~dp0web"
echo =====================================================================
echo Launching Nikkei 225 FastAPI + Modern Web Dashboard
echo URL: http://127.0.0.1:8001
echo =====================================================================
py -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
pause
