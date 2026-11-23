@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 exit /b 1

rem ------------------------------------------------------------------------
rem RV32I Project - Unified script (build, run, tests)
rem ------------------------------------------------------------------------

if /I "%~1"=="build" goto do_build
if /I "%~1"=="atomic" goto run_atomic
if /I "%~1"=="pipeline" goto run_pipeline
if /I "%~1"=="tests" goto do_tests
if not "%~1"=="" goto usage

echo.
echo ----------------------------------------------------------------
echo  RV32I RISC-V Core
echo ----------------------------------------------------------------
echo.
echo  1. Compilar proyecto
echo  2. Ejecutar core Single-Cycle (Atomic)
echo  3. Ejecutar core Pipelined (Pipeline)
echo  4. Ejecutar pruebas unitarias
echo.
set /p "OPCION=Opcion [1/2/3/4]: "
if "%OPCION%"=="1" goto do_build
if "%OPCION%"=="2" goto run_atomic
if "%OPCION%"=="3" goto run_pipeline
if "%OPCION%"=="4" goto do_tests
goto usage

:do_build
echo.
echo [1/1] Compilando modulos RV32I...
call bin\make.bat
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo.
    popd
    exit /b 1
)
echo.
echo Compilacion completada.
popd
exit /b 0

:run_atomic
echo.
echo [1/2] Compilando modulos...
call bin\make.bat
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo.
    popd
    exit /b 1
)
echo.
echo [2/2] Ejecutando core Single-Cycle (rv32-atomic)...
call simics.bat "targets\rv32i\rv32-atomic.simics"
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:run_pipeline
echo.
echo [1/2] Compilando modulos...
call bin\make.bat
if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo.
    popd
    exit /b 1
)
echo.
echo [2/2] Ejecutando core Pipelined (rv32-pipeline)...
call simics.bat "targets\rv32i\rv32-pipeline.simics"
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:do_tests
if /I "%~2"=="atomic" goto test_atomic
if /I "%~2"=="pipeline" goto test_pipeline
if /I "%~2"=="all" goto test_all
if not "%~2"=="" goto usage_tests
echo.
echo  1. Pruebas core Single-Cycle (Atomic)
echo  2. Pruebas core Pipelined (Pipeline)
echo  3. Todas las pruebas
echo.
set /p "TESTOPCION=Opcion [1/2/3]: "
if "%TESTOPCION%"=="1" goto test_atomic
if "%TESTOPCION%"=="2" goto test_pipeline
if "%TESTOPCION%"=="3" goto test_all
goto usage_tests

:test_atomic
echo.
echo ----------------------------------------------------------------
echo  Pruebas: Core Single-Cycle (Atomic)
echo ----------------------------------------------------------------
call bin\mini-python.bat tests\rv32-atomic\test_atomic.py
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:test_pipeline
echo.
echo ----------------------------------------------------------------
echo  Pruebas: Core Pipelined (Pipeline)
echo ----------------------------------------------------------------
call bin\mini-python.bat tests\rv32-pipeline\test_pipeline.py
set "RESULT=%ERRORLEVEL%"
popd
exit /b %RESULT%

:test_all
echo.
echo ----------------------------------------------------------------
echo  Pruebas: Todos los cores (Atomic + Pipeline)
echo ----------------------------------------------------------------
echo.
echo [1/2] Core Single-Cycle (Atomic)
echo ----------------------------------------------------------------
call bin\mini-python.bat tests\rv32-atomic\test_atomic.py
set "RESULT_ATOMIC=%ERRORLEVEL%"
if %RESULT_ATOMIC% NEQ 0 (
    echo.
    echo ERROR: Pruebas del core Atomic fallaron.
    popd
    exit /b %RESULT_ATOMIC%
)
echo.
echo [2/2] Core Pipelined (Pipeline)
echo ----------------------------------------------------------------
call bin\mini-python.bat tests\rv32-pipeline\test_pipeline.py
set "RESULT_PIPELINE=%ERRORLEVEL%"
if %RESULT_PIPELINE% NEQ 0 (
    echo.
    echo ERROR: Pruebas del core Pipeline fallaron.
    popd
    exit /b %RESULT_PIPELINE%
)
echo.
echo ----------------------------------------------------------------
echo  TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE
echo ----------------------------------------------------------------
popd
exit /b 0

:usage
echo.
echo Uso: %~nx0 [build | atomic | pipeline | tests [atomic | pipeline | all]]
echo.
echo   build   : Compila los modulos RV32I
echo   atomic  : Ejecuta el core Single-Cycle en Simics
echo   pipeline: Ejecuta el core Pipelined en Simics
echo   tests   : Ejecuta pruebas unitarias (atomic | pipeline | all)
echo.
popd
exit /b 2

:usage_tests
echo.
echo Uso: %~nx0 tests [atomic | pipeline | all]
echo.
echo   atomic  : Pruebas del core Single-Cycle
echo   pipeline: Pruebas del core Pipelined
echo   all     : Ambas suites de pruebas
echo.
popd
exit /b 2
