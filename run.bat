@echo off
setlocal
cd /d %~dp0
call .venv\Scripts\activate.bat
if not exist data\duckdb\abhedya.duckdb (
  echo Database not found. Running ingestion first...
  python scripts\prepare_data.py --csv data\raw\VoidHacks8_MuleAccount_2M_Transactions.csv
)
start "Abhedya-Chakra API" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8000
