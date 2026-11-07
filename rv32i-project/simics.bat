@echo off
rem this file will be overwritten by the project setup script
setlocal
set SIMICS_BASE_PACKAGE=C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0
if "%SIMICS_PYTHON_PACKAGE%"=="" (
    set SIMICS_PYTHON_PACKAGE=
)
set "SIMICS_PYTHON=%~dp0.\python.bat"
"C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0\bin\simics.bat" --project "E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project" %*
