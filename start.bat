@echo off
setlocal
set "PROJECT_DIR=%~dp0"
set "PYTHON_EXE=%PROJECT_DIR%Backend\venv\Scripts\python.exe"

if /I "%~1"=="--backend" goto backend
if /I "%~1"=="--frontend" goto frontend

echo.
echo  KAIROS - Monitor de embarque
echo  ===========================
echo.

if not exist "%PYTHON_EXE%" (
    echo [ERRO] Ambiente virtual do backend nao encontrado.
    echo Instale o backend conforme Backend\README.md.
    goto failure
)
where node >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado. Instale o Node.js 22.12 ou superior.
    goto failure
)
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERRO] npm nao encontrado no PATH.
    goto failure
)
"%PYTHON_EXE%" -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo [ERRO] A dependencia websockets nao esta instalada.
    echo Execute no Backend: venv\Scripts\python.exe -m pip install -r requirements.txt
    goto failure
)
if not exist "%PROJECT_DIR%Frontend\node_modules\vite\bin\vite.js" (
    if /I "%~1"=="--check" (
        echo [ERRO] Dependencias do frontend nao instaladas. Execute npm install em Frontend.
        exit /b 1
    )
    echo Instalando dependencias do frontend...
    pushd "%PROJECT_DIR%Frontend"
    call npm install
    if errorlevel 1 (
        popd
        goto failure
    )
    popd
)
if /I "%~1"=="--check" (
    echo [OK] Backend e frontend prontos para iniciar.
    exit /b 0
)

echo Iniciando backend e frontend em janelas separadas...
start "Kairos - Backend" "%ComSpec%" /k call "%~f0" --backend
start "Kairos - Frontend" "%ComSpec%" /k call "%~f0" --frontend
echo.
echo Painel: http://127.0.0.1:5173
echo Socket: ws://127.0.0.1:8765
echo O backend pode levar alguns segundos para carregar YOLO e OCR.
echo Para encerrar, pressione Ctrl+C nas duas janelas.
timeout /t 4 /nobreak >nul
start "" "http://127.0.0.1:5173"
exit /b 0

:backend
cd /d "%PROJECT_DIR%Backend"
"%PYTHON_EXE%" src\main.py --headless --ws-host 127.0.0.1 --ws-port 8765 --stream-fps 30 --keep-dashboard
exit /b %errorlevel%

:frontend
cd /d "%PROJECT_DIR%Frontend"
call npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
exit /b %errorlevel%

:failure
if /I not "%~1"=="--check" pause
exit /b 1
