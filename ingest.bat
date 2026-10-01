@echo off
setlocal
cd /d %~dp0
call .venv\Scripts\activate.bat
python scripts\prepare_data.py --csv data\raw\VoidHacks8_MuleAccount_2M_Transactions.csv
pause
