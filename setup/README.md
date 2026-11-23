# Setup Process — RV32I RISC-V Core (Windows)

Carpeta con todo lo necesario para instalar y configurar el proyecto en **cualquier equipo Windows**, desde cero:

| Archivo | Descripción |
|---------|-------------|
| [`SETUP_PROCESS.md`](SETUP_PROCESS.md) | Guía paso a paso (manual y automatizada) |
| [`install-dependencies.bat`](install-dependencies.bat) | Instalador de dependencias (Simics, MinGW, Python, CMake/Ninja, libs Python) |
| [`configure-project.bat`](configure-project.bat) | Ajusta las rutas hardcodeadas al usuario actual |
| [`verify-setup.bat`](verify-setup.bat) | Verifica que el entorno esté listo para correr scripts `.bat` y `.py` |

## Flujo rápido

```bat
rem 1. Instalar dependencias del sistema
setup\install-dependencies.bat

rem 2. Configurar rutas del proyecto para este usuario
setup\configure-project.bat

rem 3. Verificar que todo funciona
setup\verify-setup.bat

rem 4. (Opcional) Compilar y correr el proyecto
rv32i-project\run-rv32i.bat build
rv32i-project\run-rv32i.bat tests all
```

> **Nota:** La instalación de **Simics** requiere el archivo `simics_installation.pdf` (raíz del repositorio) y la licencia/instalador de Intel. Ese paso es semi-manual porque Simics no es un instalador silencioso público.
