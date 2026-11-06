@echo off
setlocal
cd /d "%~dp0"
title COINPILOT AI - MASTER OWNER
echo.
echo  ==============================================
echo       COINPILOT AI - MASTER OWNER v1.4
echo       Level 50 / 50 - VIRTUAL + MANUAL REAL MODE
echo  ==============================================
echo.
where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py -3
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11 or newer was not found.
    echo Install it from https://www.python.org/downloads/windows/
    echo IMPORTANT: enable "Add Python to PATH".
    pause
    exit /b 1
  )
  set PY=python
)
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating private environment...
  %PY% -m venv .venv
  if errorlevel 1 goto failed
)
echo [2/3] Installing required components...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto failed
echo [3/3] Launching CoinPilot...
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto failed
goto end
:failed
echo.
echo Launch failed. Check your internet connection and Python installation.
echo Read INSTALLATION_GUIDE.txt for troubleshooting.
pause
:end
endlocal
