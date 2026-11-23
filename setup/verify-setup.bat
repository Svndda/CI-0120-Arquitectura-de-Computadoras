@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0.."
set "PROJECT_DIR=%CD%\rv32i-project"
set "SIMICS_BASE=C:\Users\%USERNAME%\AppData\Local\Programs\Simics\simics-7.113.0"

set "FAILS=0"
set "CHECKS=0"

echo.
echo =========================================================================
echo  RV32I RISC-V Core - Verificacion de entorno
echo =========================================================================
echo.

:check_ok
set /a CHECKS+=1
echo [%CHECKS%] %~1 ....................... OK
exit /b 0

:check_fail
set /a CHECKS+=1
set /a FAILS+=1
echo [%CHECKS%] %~1 ....................... FALTA / ERROR
exit /b 0

if exist "%SIMICS_BASE%\bin\simics.bat" (
    call :check_ok "Simics 7.113.0"
) else (
    call :check_fail "Simics 7.113.0 en %SIMICS_BASE%"
)

if exist "%SIMICS_BASE%\bin\mini-python.bat" (
    call :check_ok "Simics mini-python.bat"
) else (
    call :check_fail "Simics mini-python.bat"
)

set "MINGW_MAKE=C:\mingw64\bin\mingw32-make.exe"
if exist "%MINGW_MAKE%" (
    "%MINGW_MAKE%" --version >nul 2>&1
    if %errorlevel% equ 0 (
        call :check_ok "MinGW-w64 mingw32-make (4.1+)"
    ) else (
        call :check_fail "MinGW-w64 mingw32-make (no responde)"
    )
) else (
    call :check_fail "MinGW-w64 mingw32-make en C:\mingw64\bin"
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        call :check_ok "Python en PATH"
    ) else (
        call :check_fail "Python (comando roto en PATH)"
    )
) else (
    call :check_fail "Python en PATH"
)

if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    call :check_ok "Entorno virtual .venv"
) else (
    call :check_fail "Entorno virtual .venv (ejecuta configure-project.bat)"
)

if exist "%PROJECT_DIR%\.venv\Scripts\python.exe" (
    "%PROJECT_DIR%\.venv\Scripts\python.exe" -c "import wx; print(wx.__version__)" >nul 2>&1
    if %errorlevel% equ 0 (
        call :check_ok "wxPython (GUI)"
    ) else (
        echo [%CHECKS%] wxPython (GUI) ....................... OPCIONAL (no instalado)
        set /a CHECKS+=1
    )
) else (
    echo [%CHECKS%] wxPython (GUI) ....................... SALTADO (no hay .venv)
    set /a CHECKS+=1
)

where cmake >nul 2>&1
if %errorlevel% equ 0 (
    call :check_ok "CMake"
) else (
    echo [%CHECKS%] CMake ....................... OPCIONAL (no instalado)
    set /a CHECKS+=1
)
where ninja >nul 2>&1
if %errorlevel% equ 0 (
    call :check_ok "Ninja"
) else (
    echo [%CHECKS%] Ninja ....................... OPCIONAL (no instalado)
    set /a CHECKS+=1
)

echo.
echo [Compilacion] Probando make.bat en %PROJECT_DIR%...
pushd "%PROJECT_DIR%" >nul 2>&1
if %errorlevel% equ 0 (
    call bin\make.bat --version >nul 2>&1
    if %errorlevel% equ 0 (
        call :check_ok "Compilacion con mingw32-make"
    ) else (
        call :check_fail "Compilacion con mingw32-make"
    )
    popd >nul 2>&1
) else (
    call :check_fail "No se pudo acceder a %PROJECT_DIR%"
)

echo.
echo =========================================================================
if %FAILS% equ 0 (
    echo  RESULTADO: TODO OK (%CHECKS% verificaciones pasadas)
    echo  El entorno esta listo para correr:
    echo    cd rv32i-project
    echo    run-rv32i.bat tests all
    exit /b 0
) else (
    echo  RESULTADO: %FAILS% de %CHECKS% verificaciones FALLARON
    echo  Revisa SETUP_PROCESS.md e instala lo que falta.
    exit /b 1
)
