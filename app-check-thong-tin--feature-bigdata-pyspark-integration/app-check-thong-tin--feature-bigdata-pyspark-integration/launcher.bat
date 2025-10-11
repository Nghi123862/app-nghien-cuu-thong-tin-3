@echo off
setlocal ENABLEDELAYEDEXPANSION
set "ROOT=%~dp0"
cd /d "%ROOT%"

:: Detect Python launcher or python.exe
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PYCMD=py -3"
) else (
  where python >nul 2>nul
  if %ERRORLEVEL%==0 (
    set "PYCMD=python"
  ) else (
    echo Khong tim thay Python. Vui long cai dat Python 3.10+ va chay lai.
    echo Tai: https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
)

if not exist ".venv" (
  %PYCMD% -m venv ".venv"
  if %ERRORLEVEL% NEQ 0 (
    echo Tao virtualenv that bai.
    pause
    exit /b 1
  )
)

set "VENV_PY=.venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
  echo Khong tim thay %VENV_PY%.
  echo Vui long xoa thu muc .venv va chay lai launcher.
  pause
  exit /b 1
)

"%VENV_PY%" -m ensurepip --upgrade
if %ERRORLEVEL% NEQ 0 (
  echo Khoi tao pip that bai.
  pause
  exit /b 1
)

"%VENV_PY%" -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
  echo Cap nhat pip that bai.
  pause
  exit /b 1
)

"%VENV_PY%" -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
  echo Cai dat thu vien that bai. Vui long kiem tra mang hoac thu lai.
  pause
  exit /b 1
)

"%VENV_PY%" app.py
if %ERRORLEVEL% NEQ 0 (
  echo Ung dung gap loi khi chay. Vui long chup man hinh thong bao nay va gui lai cho toi.
  pause
  exit /b 1
)

endlocal
