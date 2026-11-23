@echo off
setlocal enabledelayedexpansion

set "SKIP_PYTHON=0"
set "SKIP_CMAKE=0"

for %%a in (%*) do (
    if /I "%%a"=="--skip-python" set "SKIP_PYTHON=1"
    if /I "%%a"=="--skip-cmake" set "SKIP_CMAKE=1"
)

echo.
echo =========================================================================
echo  RV32I RISC-V Core - Instalador de dependencias (Windows)
echo =========================================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ADVERTENCIA] Este script requiere privilegios de administrador.
    echo               Algunos pasos podrían fallar sin ellos.
    echo               Ejecuta la terminal como Administrador y vuelve a correr este script.
    echo.
    set /p "CONTINUAR=¿Deseas continuar de todas formas? (s/N): "
    if /I "!CONTINUAR!" neq "s" (
        echo Instalación cancelada.
        exit /b 1
    )
)

reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f >nul 2>&1
if %errorlevel% equ 0 (
    echo       OK: LongPathsEnabled = 1
) else (
    echo       AVISO: No se pudo habilitar LongPathsEnabled (requiere reinicio o admin).
)

set "HAVE_WINGET=0"
where winget >nul 2>&1
if %errorlevel% equ 0 set "HAVE_WINGET=1"

set "HAVE_CURL=0"
where curl >nul 2>&1
if %errorlevel% equ 0 set "HAVE_CURL=1"

set "HAVE_TAR=0"
where tar >nul 2>&1
if %errorlevel% equ 0 set "HAVE_TAR=1"

set "HAVE_PS=0"
where powershell >nul 2>&1
if %errorlevel% equ 0 set "HAVE_PS=1"

echo       winget:      %HAVE_WINGET%
echo       curl:        %HAVE_CURL%
echo       tar:         %HAVE_TAR%
echo       powershell:  %HAVE_PS%

set "MINGW_DIR=C:\mingw64"
set "MINGW_MAKE=%MINGW_DIR%\bin\mingw32-make.exe"

if exist "%MINGW_MAKE%" (
    echo       MinGW-w64 ya existe en %MINGW_DIR%. Saltando.
) else (
    if %HAVE_WINGET% equ 1 (
        echo       Intentando instalar MinGW-w64 vía winget...
        winget install --id "eXoCorporation.MINGW-packages" --source winget --accept-package-agreements --accept-source-agreements --location "C:\" >nul 2>&1
        if %errorlevel% equ 0 (
            echo       OK: MinGW-w64 instalado vía winget.
        ) else (
            echo       AVISO: winget no pudo instalar MinGW-w64 automaticamente.
        )
    )

    if not exist "%MINGW_MAKE%" (
        echo       AVISO: MinGW-w64 no se encontro en %MINGW_DIR%.
        echo               Instalalo manualmente desde https://winlibs.com/
       echo               y asegurate de que exista: %MINGW_MAKE%
        echo               (version 4.1 o superior).
    )
)

if exist "%MINGW_MAKE%" (
    echo       Verificando version de mingw32-make...
    "%MINGW_MAKE%" --version | findstr /r /c:"GNU Make" >nul 2>&1
    if %errorlevel% equ 0 (
        echo       OK: mingw32-make disponible.
    ) else (
        echo       AVISO: mingw32-make no responde correctamente.
    )
) else (
    set "MINGW_OK=0"
)

if %SKIP_PYTHON% equ 1 (
    echo       Saltando instalacion de Python (--skip-python).
) else (
    echo       Instalando Python 3.11+...
    set "PYTHON_OK=0"
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        echo       Python ya esta en el PATH: !PYTHON_PATH!
        set "PYTHON_OK=1"
    ) else if %HAVE_WINGET% equ 1 (
        echo       Instalando Python vía winget...
        winget install --id "Python.Python.3.11" --source winget --accept-package-agreements --accept-source-agreements >nul 2>&1
        if %errorlevel% equ 0 set "PYTHON_OK=1"
    )
    if %PYTHON_OK% equ 1 (
        where python >nul 2>&1
        if %errorlevel% equ 0 (
            echo       OK: Python instalado.
            python --version
        ) else (
            echo       AVISO: Python no queda en el PATH despues de instalar.
            echo               Reinicia la terminal o agregalo manualmente al PATH.
        )
    ) else (
        echo       AVISO: No se pudo instalar Python automaticamente.
        echo               Descargalo de https://www.python.org/downloads/windows/
        echo               y marca "Add Python to PATH" durante la instalacion.
    )
)

if %SKIP_CMAKE% equ 1 (
    echo       Saltando CMake/Ninja (--skip-cmake).
) else (
    echo       Instalando CMake 3.22+ y Ninja...
    if %HAVE_WINGET% equ 1 (
        winget install --id "Kitware.CMake" --source winget --accept-package-agreements --accept-source-agreements >nul 2>&1
        winget install --id "Ninja-build.Ninja" --source winget --accept-package-agreements --accept-source-agreements >nul 2>&1
    )
    where cmake >nul 2>&1 && echo       OK: CMake disponible || echo       AVISO: CMake no se encontro.
    where ninja >nul 2>&1 && echo       OK: Ninja disponible   || echo       AVISO: Ninja no se encontro.
)

echo.
echo =========================================================================
echo  Siguiente paso:
echo    1. Ejecuta: setup\configure-project.bat   (ajusta rutas al usuario actual)
echo    2. Ejecuta: setup\verify-setup.bat        (verifica el entorno)
echo    3. Ve a rv32i-project y corre: run-rv32i.bat
echo =========================================================================
echo.
pause
exit /b 0
