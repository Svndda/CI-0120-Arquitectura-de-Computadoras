# Setup Process — RV32I RISC-V Core (Windows)

Este documento describe cómo instalar **todas las dependencias necesarias** para correr el proyecto `rv32i-project` en **cualquier equipo Windows**, desde la instalación de Simics hasta la ejecución de scripts `.bat` y `.python`.

El proyecto simula dos cores RISC-V RV32I (single-cycle "atomic" y pipelined de 4 etapas) sobre **Intel Simics 7.113.0**.

---

## 1. Requisitos previos del equipo

| Requisito | Mínimo / Recomendado |
|-----------|----------------------|
| Sistema operativo | Windows 10 o Windows 11 (64 bits) |
| Arquitectura | x86_64 (amd64) |
| RAM | 8 GB mínimo / 16 GB recomendado |
| Espacio en disco | ~15 GB libres (Simics + toolchains + proyecto) |
| Privilegios | Administrador (para instalar software y escribir en `C:\`) |
| Conexión a internet | Para descargar instaladores y librerías Python |

> Si el equipo está detrás de un proxy corporativo, configúralo antes de empezar:
> ```bat
> set HTTP_PROXY=http://usuario:pass@proxy:8080
> set HTTPS_PROXY=http://usuario:pass@proxy:8080
> ```

---

## 2. Resumen de dependencias y dónde se instalan

| Componente | Versión | Ruta por defecto | Uso en el proyecto |
|------------|---------|------------------|--------------------|
| **Intel Simics** | 7.113.0 | `C:\Users\%USERNAME%\AppData\Local\Programs\Simics\simics-7.113.0` | Simulación de los cores RV32I; ejecuta los targets `.simics` |
| **MinGW-w64** | make 4.1+ | `C:\mingw64\bin\mingw32-make.exe` | Compila los módulos C de los cores (`bin\make.bat`) |
| **Python** | 3.11+ | `C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe` | Entorno virtual `.venv` para scripts de prueba |
| **wxPython** | ~4.2.1 | — (pip) | Solo si usas la GUI de Simics (`gui-requirements.txt`) |
| **CMake** | 3.22+ | `C:\Program Files\CMake\bin\cmake.exe` | Opcional, build alternativo con `CMakeLists.txt` |
| **Ninja** | latest | `C:\Program Files\Ninja\ninja.exe` | Opcional, generador para CMake |

> **Python:** los tests del proyecto usan únicamente la **biblioteca estándar** de Python (`importlib`, `pathlib`, `re`, `subprocess`, `unittest`, `mock`). No se requieren paquetes externos para correr las pruebas unitarias. `wxPython` solo es necesario si vas a lanzar la interfaz gráfica de Simics.

---

## 3. Paso a paso (manual)

Sigue este orden en un equipo limpio.

### 3.1 Instalar Simics 7.113.0

Simics es un producto comercial de Intel. El proceso está detallado en:

```
simics_installation.pdf   (raíz del repositorio)
```

Resumen del procedimiento:

1. Obtén el instalador de Simics y tu licencia de Intel.
2. Ejecuta el instalador.
3. Cuando te pregunte el destino, elige:
   ```
   C:\Users\%USERNAME%\AppData\Local\Programs\Simics\simics-7.113.0
   ```
   *(Usar `%USERNAME%` hace que la ruta funcione en cualquier equipo sin editar scripts.)*
4. Completa la instalación y asegúrate de que existan estos ejecutables:
   - `...\simics-7.113.0\bin\simics.bat`
   - `...\simics-7.113.0\bin\mini-python.bat`
   - `...\simics-7.113.0\bin\setup-venv.bat`
   - `...\simics-7.113.0\bin\project-setup.bat`

> Si instalas Simics en otra ruta, tendrás que editar `rv32i-project\simics.bat`, `rv32i-project\bin\make.bat`, `rv32i-project\bin\mini-python.bat`, `rv32i-project\bin\project-setup.bat` y `rv32i-project\config.mk`, o bien usar `setup\configure-project.bat` (ver sección 4).

### 3.2 Instalar MinGW-w64 (make)

El proyecto compila módulos C con `mingw32-make.exe`.

1. Descarga el instalador de MinGW-w64 (por ejemplo, desde https://winlibs.com/ o https://sourceforge.net/projects/mingw-w64/).
2. Instálalo en:
   ```
   C:\mingw64
   ```
3. Asegúrate de marcar para instalar la herramienta **`make`** (`mingw32-make.exe`).
4. Verifica la versión (debe ser 4.1 o superior):
   ```bat
   C:\mingw64\bin\mingw32-make.exe --version
   ```

### 3.3 Instalar Python (opcional pero recomendado)

Simics trae su propio intérprete Python (`mini-python.bat`), pero se recomienda instalar Python por separado para crear el entorno virtual `.venv` del proyecto y ejecutar scripts `.py` de forma independiente.

1. Descarga Python 3.11 o superior desde https://www.python.org/downloads/windows/.
2. Ejecuta el instalador y marca **ambas** casillas:
   - [x] **Add Python to PATH**
   - [x] **Install for all users** (o al menos para el usuario actual)
3. Ruta sugerida:
   ```
   C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\
   ```
4. Verifica:
   ```bat
   python --version
   pip --version
   ```

### 3.4 Instalar CMake y Ninja (opcional)

Solo necesarios si prefieres construir con CMake en lugar de `make.bat`.

1. Descarga e instala CMake 3.22+ desde https://cmake.org/download/.
   - Durante la instalación, marca **"Add CMake to the system PATH para todos los usuarios"**.
2. Descarga Ninja desde https://github.com/ninja-build/ninja/releases y copia `ninja.exe` a una carpeta del PATH, por ejemplo:
   ```
   C:\Program Files\Ninja\ninja.exe
   ```
3. Verifica:
   ```bat
   cmake --version
   ninja --version
   ```

### 3.5 Clonar o copiar el proyecto

```bat
git clone <url-del-repositorio>
cd CI-0120-Arquitectura-de-Computadoras
```

O copia la carpeta `rv32i-project` al equipo destino.

---

## 4. Configuración automatizada del proyecto (recomendado)

Los scripts `.bat` del proyecto contienen **rutas hardcodeadas** al usuario `aaron` (quien creó el repo). Para que funcionen en cualquier equipo, ejecuta:

```bat
setup\configure-project.bat
```

Este script detecta el `%USERNAME%` actual y reescribe las rutas de:
- `rv32i-project\simics.bat`
- `rv32i-project\bin\make.bat`
- `rv32i-project\bin\mini-python.bat`
- `rv32i-project\bin\project-setup.bat`
- `rv32i-project\bin\setup-venv.bat`
- `rv32i-project\config.mk`

Luego crea el entorno virtual y instala las dependencias Python:

```bat
rv32i-project\bin\setup-venv.bat
cd rv32i-project
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r gui-requirements.txt   <- solo si usas GUI
```

> `requirements.txt` está vacío porque los tests usan solo stdlib. `gui-requirements.txt` contiene `wxPython~=4.2.1`.

---

## 5. Scripts de instalación automatizados

### 5.1 `setup\install-dependencies.bat`

Descarga e instala MinGW-w64, Python, CMake y Ninja automáticamente. Requiere privilegios de administrador.

Uso:
```bat
setup\install-dependencies.bat
```

Opciones:
```bat
setup\install-dependencies.bat --skip-python   # omite Python si ya está instalado
setup\install-dependencies.bat --skip-cmake    # omite CMake/Ninja
```

### 5.2 `setup\configure-project.bat`

Ajusta rutas hardcodeadas al usuario actual y crea el venv.

Uso:
```bat
setup\configure-project.bat
```

### 5.3 `setup\verify-setup.bat`

Comprueba que todas las herramientas estén disponibles y que el proyecto compile.

Uso:
```bat
setup\verify-setup.bat
```

---

## 6. Ejecutar los scripts del proyecto

Desde la carpeta `rv32i-project`:

```bat
rem Menú interactivo
run-rv32i.bat

rem Compilar módulos C de ambos cores
run-rv32i.bat build

rem Ejecutar core Single-Cycle (atomic) en Simics
run-rv32i.bat atomic

rem Ejecutar core Pipelined en Simics
run-rv32i.bat pipeline

rem Ejecutar pruebas unitarias
run-rv32i.bat tests atomic
run-rv32i.bat tests pipeline
run-rv32i.bat tests all
```

### Ejecutar scripts `.bat` individuales

Todos los `.bat` de `rv32i-project\bin\` delegan en Simics o en `mingw32-make`. Ejemplos:

```bat
bin\simics.bat targets\rv32i\rv32-atomic.simics
bin\python.bat tests\rv32-atomic\test_atomic.py
bin\make.bat
```

### Ejecutar scripts `.py` directamente

Con el entorno virtual activado:

```bat
rv32i-project\.venv\Scripts\activate.bat
python tests\rv32-atomic\test_atomic.py
python tests\rv32-pipeline\test_pipeline.py
```

O sin activar el venv (usando el ejecutable directo):

```bat
rv32i-project\.venv\Scripts\python.exe tests\rv32-atomic\test_atomic.py
```

---

## 7. Verificación final

Ejecuta `setup\verify-setup.bat`. Debe reportar `OK` en cada punto:

```
[1/6] Simics 7.113.0 ....................... OK
[2/6] MinGW-w64 mingw32-make 4.1+ .......... OK
[3/6] Python 3.11+ ......................... OK
[4/6] Entorno virtual .venv ................ OK
[5/6] wxPython (GUI) ....................... OK  (opcional)
[6/6] Compilación de prueba (make) ......... OK
```

Si todo pasa, el equipo está listo para correr `run-rv32i.bat` y cualquier script `.bat` / `.py` del proyecto.

---

## 8. Solución de problemas comunes

| Problema | Causa probable | Solución |
|----------|----------------|----------|
| `'mingw32-make' no se reconoce` | MinGW no está en el PATH | Agrega `C:\mingw64\bin` al PATH del sistema o reinstala marcando "Add to PATH" |
| `simics.bat` no encuentra Simics | Ruta hardcodeada antigua de `aaron` | Ejecuta `setup\configure-project.bat` |
| `Python no se reconoce` | Python no instalado o no en PATH | Instala Python y marca "Add Python to PATH" |
| `module not found: wxPython` | Falta librería GUI | `pip install -r rv32i-project\gui-requirements.txt` |
| Simics da error de licencia | Licencia no configurada | Sigue `simics_installation.pdf` para activar la licencia |
| Rutas con espacios fallan | Simics es sensible a espacios en rutas | Instala todo en rutas sin espacios (evita `C:\Program Files\Simics`) |
| `LONG_PATH` en Windows | Rutas largas de Simics | Habilita long paths: `reg add "HKLM\SYSTEM\CurrentControlSet\Control\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f` |

---

## 9. Checklist para equipo nuevo

- [ ] Windows 10/11 64 bits con privilegios de administrador
- [ ] Simics 7.113.0 instalado en `C:\Users\%USERNAME%\AppData\Local\Programs\Simics\simics-7.113.0` (ver `simics_installation.pdf`)
- [ ] MinGW-w64 con `mingw32-make.exe` 4.1+ en `C:\mingw64`
- [ ] Python 3.11+ en el PATH
- [ ] `setup\install-dependencies.bat` ejecutado (opcional, automatiza lo anterior)
- [ ] `setup\configure-project.bat` ejecutado (ajusta rutas al usuario actual)
- [ ] `setup\verify-setup.bat` ejecutado con resultado OK
- [ ] `rv32i-project\run-rv32i.bat tests all` pasa sin errores
