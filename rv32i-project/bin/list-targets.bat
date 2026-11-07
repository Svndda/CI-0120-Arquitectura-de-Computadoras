
@echo off
rem this file will be overwritten by the project setup script
setlocal
set SIMICS_BASE_PACKAGE=C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0
if "%SIMICS_PYTHON_PACKAGE%"=="" (
    set SIMICS_PYTHON_PACKAGE=
)
set "SIMICS_PYTHON=%~dp0..\python.bat"
if exist "E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project\.package-list" set SIMICS_EPL=--package-list "E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project\.package-list"
if not exist "E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project\.package-list" set SIMICS_EPL=
"C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0\bin\list-targets.bat" %SIMICS_EPL% --project "E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project" %*
