@echo off
title Nikkei 225 Intraday Market Behavior Research (Port 8501)
cd /d "%~dp0"
echo =====================================================================
echo Launching Nikkei 225 Market Behavior Research Dashboard
echo URL: http://localhost:8501
echo =====================================================================
..\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501
pause
