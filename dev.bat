@echo off
echo === ControlCheck AI 2.0 Dev Launcher ===
echo Starting backend API...
start "ControlCheck API" cmd /k "python -m uvicorn controlcheck.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload"
ping -n 3 127.0.0.1 >nul
echo Starting frontend web...
start "ControlCheck Web" cmd /k "npm run dev"
echo.
echo API:  http://127.0.0.1:8000
echo Web:  http://127.0.0.1:5173
echo.
