# Administrador de tareas y sistema de archivos (simulador)

Proyecto Parcial 2. Es un solo programa en Python con ventanas que simula dos herramientas de un sistema operativo:

- **Administrador de tareas:** muestra todo lo que incluye el BCP (Bloque de Control de Proceso) y permite ejecutar, pausar y detener procesos.
- **Sistema de archivos:** muestra íconos y carpetas de forma jerárquica, permite crear, modificar y eliminar archivos, y otorgar permisos de lectura, escritura y ejecución.

**Todo es simulado.** El programa no debe tocar procesos ni archivos reales de la computadora. Los datos viven en memoria y se guardan en `data/`.

## Requisitos

- Python 3.12 o superior
- Tkinter

| Sistema | Instalar Tkinter | Comprobar | Ejecutar |
|---|---|---|---|
| Linux Mint | `sudo apt install python3-tk` | `python3 -m tkinter` | `python3 main.py` |
| Windows 11 | Viene con el instalador de python.org (opción "tcl/tk and IDLE") | `py -m tkinter` | `py main.py` |

Ejecuta siempre el programa desde la carpeta raíz del proyecto.

## Estructura

```text
main.py                  Solo arranca la aplicación
data/                    Datos guardados en JSON
src/
  app.py                 Ventana principal, controladores y reloj de la simulación
  procesos/
    models.py            Clase Proceso con los datos del BCP
    controllers.py       Estados, pulsos y acciones de los procesos
    views.py             Ventanas del administrador de tareas
  archivos/
    models.py            Clases de archivos y carpetas con sus permisos
    controllers.py       Operaciones y validación de permisos
    views.py             Ventanas del sistema de archivos
```

Esta es la estructura objetivo. `src/models.py`, `src/controllers.py`, `src/views.py` y `data/tasks.json` son de la primera versión de consola y se quitarán cuando la nueva esté lista.

## Reparto del trabajo

| Programador | Sistema | Responsable de | Rama |
|---|---|---|---|
| Lógica | Linux Mint | `models.py` y `controllers.py` de ambos módulos, y los JSON de `data/` | `logica` |
| Interfaz | Windows 11 | `main.py`, `src/app.py` y `views.py` de ambos módulos | `interfaz` |

Cada quien modifica solo sus archivos. Si necesitas un cambio en los del otro, avísale primero.

## Reglas de la interfaz

- Usar un solo `Tk()` y un solo `mainloop()`. Las demás ventanas son `Toplevel`.
- Crear los controladores en `src/app.py` y pasarlos a cada ventana.
- Usar un solo reloj con `after` en `src/app.py`. No usar `sleep`, porque congela la ventana.
- Si una ventana ya está abierta, traerla al frente en lugar de crear otra.
- Las vistas no deciden reglas: piden la acción al controlador y muestran el resultado.
- Mientras no exista la lógica, usar datos de ejemplo en una lista al inicio de cada `views.py`.
- `procesos/` y `archivos/` no se importan entre sí.

## Acuerdo entre interfaz y lógica

Estos nombres permiten trabajar al mismo tiempo. Si alguno cambia, hay que actualizar esta sección y avisar al otro programador.

### Procesos

**Datos del BCP:** `pid`, `ppid`, `nombre`, `usuario`, `estado`, `contador_programa`, `registros`, `prioridad`, `tiempo_cpu`, `tiempo_restante`, `memoria_mb`, `archivos_abiertos`, `dispositivos`.

**Estados:** `Nuevo`, `Listo`, `En ejecución`, `En espera`, `Terminado`.

**Acciones del controlador:** `listar()`, `crear(nombre, prioridad, memoria_mb)`, `ejecutar(pid)`, `pausar(pid)`, `detener(pid)`, `pulso()`.

### Archivos

**Datos de cada elemento:** `nombre`, `tipo` (`archivo` o `carpeta`), `tamano`, `creado`, `modificado`, `permisos`, `contenido`, `hijos`.

**Permisos:** `lectura`, `escritura`, `ejecucion`.

**Acciones del controlador:** `listar(ruta)`, `crear(ruta, nombre, tipo)`, `leer(ruta)`, `modificar(ruta, contenido)`, `eliminar(ruta)`, `cambiar_permisos(ruta, permisos)`.

## Flujo de trabajo con Git

1. Antes de empezar: `git checkout main` y `git pull`.
2. Trabaja en tu rama: `git checkout logica` o `git checkout interfaz`. La primera vez agrega `-b` después de `checkout`.
3. Haz commits pequeños y súbelos con `git push -u origin nombre-de-tu-rama`.
4. Abre un pull request hacia `main` cuando una parte funcione.

## Entregables

- Programa funcionando
- Documento formal: portada, introducción, desarrollo y conclusión
- Presentación digital de apoyo

Se evalúa el dominio de los dos temas, la funcionalidad del programa y la puntualidad de las entregas.
