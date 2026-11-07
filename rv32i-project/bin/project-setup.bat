@echo off
rem this file will be overwritten by the project setup script
setlocal
set SIMICS_BASE_PACKAGE=C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0
if "%SIMICS_PYTHON_PACKAGE%"=="" (
    set SIMICS_PYTHON_PACKAGE=
)
set "SIMICS_PYTHON=C:\Users\aaron\AppData\Local\Python\pythoncore-3.14-64\python.exe"
"C:\Users\aaron\AppData\Local\Programs\Simics\simics-7.113.0\bin\project-setup.bat" --project "E:\Dev\Repositories\CI-0120-Arquitectura-de-Computadoras\rv32i-project" %*
