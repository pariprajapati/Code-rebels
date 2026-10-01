@echo off
setlocal
cd /d %~dp0
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
if not exist data\raw mkdir data\raw
if not exist data\duckdb mkdir data\duckdb
if not exist data\kuzu mkdir data\kuzu
if not exist outputs mkdir outputs
echo.
echo Setup complete.
pause
