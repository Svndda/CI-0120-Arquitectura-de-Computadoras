# RV32I RISC-V Core — Proyecto Etapa 2

Proyecto de arquitectura de computadoras con dos cores RV32I implementados en SIMICS:
- **Parte 1:** Core Single-Cycle (`modules/rv32-atomic`)
- **Parte 2:** Core Pipelined de 4 etapas (`modules/rv32-pipeline`)

## Uso

Desde la raíz del proyecto, ejecuta:

```bat
run-rv32i.bat [opcion] [subopcion]
```

### Opciones principales

| Comando | Qué hace |
|---------|----------|
| `run-rv32i.bat build` | Compila los módulos C de ambos cores |
| `run-rv32i.bat atomic` | Ejecuta el core Single-Cycle en SIMICS |
| `run-rv32i.bat pipeline` | Ejecuta el core Pipelined en SIMICS |
| `run-rv32i.bat tests` | Menú interactivo de pruebas |
| `run-rv32i.bat` | Menú principal interactivo |

### Pruebas unitarias

| Comando | Qué hace |
|---------|----------|
| `run-rv32i.bat tests atomic` | 10 pruebas del core Single-Cycle |
| `run-rv32i.bat tests pipeline` | 12 pruebas del core Pipelined |
| `run-rv32i.bat tests all` | Las 22 pruebas (ambos cores) |

### Ejemplos prácticos

```bat
rem Compilar todo
run-rv32i.bat build

rem Ejecutar todas las pruebas
run-rv32i.bat tests all

rem Solo pruebas del pipeline
run-rv32i.bat tests pipeline

rem Ejecutar el core atómico en SIMICS
run-rv32i.bat atomic
```

## Requisitos

- Windows con Intel SIMICS instalado
- MinGW-w64 (`mingw32-make.exe`)
- Python (vía `bin\mini-python.bat`)

Si SIMICS está en una ruta distinta a la predeterminada, edita `simics.bat` y `bin\make.bat` para ajustar `SIMICS_BASE_PACKAGE`.

## Resultado esperado

Todas las pruebas deberían terminar con estado `OK`, confirmando que ambos cores producen el mismo resultado arquitectónico (registros y PC) para cada programa de prueba.