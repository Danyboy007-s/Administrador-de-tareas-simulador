# Administrador de tareas y sistema de archivos (simulador)

Proyecto Parcial 2. Es un solo programa en Python con ventanas que simula dos herramientas de un sistema operativo:

- **Administrador de tareas:** muestra todo lo que incluye el BCP (Bloque de Control de Proceso) y permite crear, ejecutar, pausar y detener procesos. Un reloj simulado hace avanzar los procesos por sus 5 estados. Los procesos se colorean según cuánta memoria consumen.
- **Sistema de archivos:** muestra un árbol jerárquico de carpetas con íconos, permite crear, leer, modificar y eliminar archivos y carpetas, y otorgar permisos de lectura, escritura y ejecución.

Los dos módulos se conectan: en `/programas` hay programas "instalados" (firefox, vscode, roblox, minecraft...) y se pueden instalar más indicando nombre y tamaño. Un archivo con permiso de ejecución se puede **ejecutar** y aparece como un proceso nuevo en el administrador, con más memoria cuanto más pesa.

**Todo es simulado.** El programa no toca procesos ni archivos reales de la computadora. Los datos viven en memoria y se guardan en `data/procesos.json` y `data/archivos.json`.

## Requisitos

- Python 3.12 o superior
- Tkinter

| Sistema | Instalar Tkinter | Comprobar | Ejecutar |
|---|---|---|---|
| Linux Mint | `sudo apt install python3-tk` | `python3 -m tkinter` | `python3 main.py` |
| Windows 11 | Viene con el instalador de python.org (opción "tcl/tk and IDLE") | `py -m tkinter` | `py main.py` |

Ejecuta siempre el programa desde la carpeta raíz del proyecto.

Para volver a los datos de ejemplo, borra los archivos de `data/`; el programa los crea de nuevo al arrancar. Esos JSON no se suben a Git.

## Estructura

```text
main.py                  Solo arranca la aplicación
data/                    Datos guardados en JSON (se crean al usar el programa)
src/
  app.py                 Ventana principal, controladores, reloj y unión entre módulos
  procesos/
    models.py            Clase Proceso con los datos del BCP y los 5 estados
    controllers.py       Transiciones, planificador, pulsos y acciones
    views.py             Ventana del administrador de tareas
  archivos/
    models.py            Clase Elemento (archivo o carpeta) con sus permisos
    controllers.py       Rutas, operaciones y validación de permisos
    views.py             Ventana del sistema de archivos
```

El programa sigue el patrón **modelo - vista - controlador**: los modelos guardan datos, los controladores deciden las reglas y las vistas solo muestran y piden acciones.

## Administrador de tareas

**Datos del BCP:** `pid`, `ppid`, `nombre`, `usuario`, `estado`, `contador_programa`, `registros`, `prioridad`, `tiempo_cpu`, `tiempo_restante`, `memoria_mb`, `archivos_abiertos`, `dispositivos`, `critico`.

**Procesos críticos del sistema:** `systemd` (PID 1) y `Xorg` (servidor gráfico) arrancan con el programa, son de `root` y nunca terminan solos (tiempo restante ∞). Si el usuario intenta pausarlos o detenerlos aparece el aviso "¿Sabes lo que haces?". Si confirma que quiere detener uno, el sistema simulado sufre un fallo crítico y el programa se cierra, como pasaría al detener System32 en Windows o el PID 1 en Linux.

**Consumo:** cada proceso se colorea según su memoria y la tabla se ordena de mayor a menor consumo:

| Consumo | Memoria | Color |
|---|---|---|
| Alto | 1000 MB o más | rojo |
| Medio | de 300 a 999 MB | amarillo |
| Bajo | menos de 300 MB | verde |
| — | proceso terminado (ya liberó su memoria) | gris |

**Estados y transiciones permitidas:**

| Desde | Puede pasar a |
|---|---|
| Nuevo | Listo, Terminado |
| Listo | En ejecución, En espera (pausa), Terminado |
| En ejecución | Listo, En espera, Terminado |
| En espera | Listo, Terminado |
| Terminado | (ninguno) |

**Reloj:** cada segundo el controlador da un pulso: admite los procesos nuevos, el planificador da el CPU si está libre, y el proceso en ejecución avanza una instrucción. Se simula un solo CPU.

**Planificador (round robin):** el CPU se da al proceso que lleva más tiempo esperando en la cola de Listos. Cada proceso usa el CPU durante su *quantum* y luego vuelve al final de la cola (cambio de contexto). Su BCP guarda el contador de programa y los registros para continuar después.

**Prioridad:** de 0 a 10. El número más bajo es el más importante, como en Linux. La prioridad define el quantum: prioridad 0 usa 6 pulsos seguidos y prioridad 10 solo 1.

**Al iniciar el programa** es como encender el equipo: los procesos de la sesión anterior ya no existen y solo arrancan los del sistema. `data/procesos.json` es una foto de la sesión actual (parecido a `/proc` en Linux). Un proceso Terminado no se puede volver a ejecutar; hay que crear o ejecutar uno nuevo.

**Acciones del controlador:** `listar()`, `crear(nombre, prioridad, memoria_mb, archivos_abiertos=None)`, `ejecutar(pid)`, `pausar(pid)`, `detener(pid)`, `relanzar(pid)`, `pulso()`.

- **Pausar** funciona con un proceso en ejecución o en Listo (esperando turno). Queda En espera y el planificador no le da el CPU hasta que se pulse **Ejecutar**, que lo reanuda.
- **Detener** lo termina y libera sus recursos. Un proceso Terminado no revive: al pulsar **Ejecutar** sobre él, el programa ofrece abrirlo de nuevo como un proceso nuevo con otro PID (`relanzar`). `listar()` agrega a cada BCP el campo `consumo` (`Alto`, `Medio`, `Bajo` o `—`).

`crear`, `ejecutar`, `pausar` y `detener` devuelven el BCP actualizado como diccionario. Si la acción no se permite, lanzan `ValueError` con un mensaje para mostrar al usuario.

## Sistema de archivos

**Datos de cada elemento:** `nombre`, `tipo` (`archivo` o `carpeta`), `tamano` (bytes), `creado`, `modificado`, `permisos`, `contenido`, `hijos`.

**Permisos** (`lectura`, `escritura`, `ejecucion`), como `rwx` en Linux:

| Acción | Permiso que pide |
|---|---|
| Entrar a una carpeta | ejecución y lectura en la carpeta |
| Leer un archivo | lectura en el archivo |
| Modificar un archivo | escritura en el archivo |
| Ejecutar un archivo | ejecución en el archivo |
| Crear o eliminar | escritura en la carpeta padre |
| Cambiar permisos | siempre se permite (como `chmod` del dueño) |

**Acciones del controlador:** `listar(ruta)`, `crear(ruta, nombre, tipo)`, `leer(ruta)`, `modificar(ruta, contenido)`, `eliminar(ruta)`, `ejecutar(ruta)`, `instalar(nombre, tamano_mb)`, `cambiar_permisos(ruta, permisos)`.

**Programas:** `instalar` crea un ejecutable en `/programas` con el tamaño indicado y permisos `r-x` (se puede leer y ejecutar, pero no modificar, como en `/usr/bin`). Al ejecutarlo, `app.py` crea un proceso que usa tantos MB de memoria como pesa el programa (mínimo 4 MB).

Los errores son `ValueError` (dato no válido), `PermissionError` (falta un permiso) y `FileNotFoundError` (la ruta no existe).

## Reglas del código

- Un solo `Tk()` y un solo `mainloop()`. Las demás ventanas son `Toplevel`.
- Los controladores se crean en `src/app.py` y se pasan a cada ventana.
- Un solo reloj con `after` en `src/app.py`. No se usa `sleep`, porque congela la ventana.
- Si una ventana ya está abierta, se trae al frente en lugar de crear otra.
- Las vistas no deciden reglas: piden la acción al controlador y muestran el resultado.
- `procesos/` y `archivos/` no se importan entre sí. `app.py` los une (por ejemplo, al ejecutar un archivo).

## Entregables

- Programa funcionando
- Documento formal: portada, introducción, desarrollo y conclusión
- Presentación digital de apoyo

Se evalúa el dominio de los dos temas, la funcionalidad del programa y la puntualidad de las entregas.
