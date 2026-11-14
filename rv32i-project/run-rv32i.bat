@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

if /I "%~1"=="atomic" (
    set "TARGET=targets\rv32i\rv32-atomic.simics"
    goto run
)
if /I "%~1"=="pipeline" (
    set "TARGET=targets\rv32i\rv32-pipeline.simics"
    goto run
)
if not "%~1"=="" goto usage

echo Selecciona el core RV32I:
echo   1. Atomic
echo   2. Pipeline
set /p "CORE=Opcion [1/2]: "
if "%CORE%"=="1" set "TARGET=targets\rv32i\rv32-atomic.simics"
if "%CORE%"=="2" set "TARGET=targets\rv32i\rv32-pipeline.simics"
if not defined TARGET goto usage

:run
echo Compilando el proyecto...
call bin\make.bat
if errorlevel 1 (
    echo Error: la compilacion fallo.
    popd
    exit /b 1
)

echo Iniciando Simics con %TARGET%...
call simics.bat "%TARGET%"
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:usage
echo Uso: %~nx0 [atomic^|pipeline]
popd
exit /b 2
