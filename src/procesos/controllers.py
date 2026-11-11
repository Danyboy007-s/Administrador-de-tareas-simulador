# Lógica del administrador de tareas: cambios de estado, acciones y reloj.
# La interfaz NO cambia los procesos directamente: llama a estas funciones
# y muestra lo que devuelven. Si algo no se permite, se lanza ValueError
# con un mensaje que la interfaz puede mostrar en un messagebox.

import json
import random
from pathlib import Path

from src.procesos.models import (
    Proceso,
    NUEVO,
    LISTO,
    EN_EJECUCION,
    EN_ESPERA,
    TERMINADO,
)

# Ruta del JSON calculada a partir de la ubicación de ESTE archivo
# (src/procesos/controllers.py -> subir 3 niveles = raíz del proyecto).
# Así funciona aunque el programa se ejecute desde otra carpeta.
RUTA = Path(__file__).resolve().parents[2] / "data" / "procesos.json"

# Tabla de transiciones: para cada estado, a qué estados se puede pasar.
# Es el diagrama de 5 estados de un sistema operativo:
#   Nuevo -> Listo            (el sistema admite el proceso)
#   Listo -> En ejecución     (el planificador le da el CPU)
#   En ejecución -> Listo     (otro proceso le quita el CPU)
#   En ejecución -> En espera (se pausa / espera E/S)
#   En espera -> Listo        (se reanuda)
#   Cualquiera -> Terminado   (termina o se detiene)
# Terminado no puede pasar a ningún otro estado.
TRANSICIONES = {
    NUEVO: (LISTO, TERMINADO),
    LISTO: (EN_EJECUCION, TERMINADO),
    EN_EJECUCION: (LISTO, EN_ESPERA, TERMINADO),
    EN_ESPERA: (LISTO, TERMINADO),
    TERMINADO: (),
}

# Procesos que aparecen la primera vez, cuando el JSON está vacío,
# para que el administrador no arranque en blanco.
# (nombre, prioridad, memoria_mb)
PROCESOS_EJEMPLO = [
    ("systemd", 0, 12),
    ("bash", 2, 4),
    ("firefox", 1, 350),
]


class AdministradorProcesos:
    def __init__(self):
        self.procesos = self.cargar()
        if not self.procesos:
            for nombre, prioridad, memoria in PROCESOS_EJEMPLO:
                self.crear(nombre, prioridad, memoria)

    # ------------------------------------------------------------------
    # Guardar y cargar
    # ------------------------------------------------------------------

    def cargar(self):
        # Si el archivo no existe o está vacío, se empieza sin procesos.
        if not RUTA.exists():
            return []
        texto = RUTA.read_text(encoding="utf-8").strip()
        if not texto:
            return []
        return [Proceso.from_dict(d) for d in json.loads(texto)]

    def guardar(self):
        datos = [p.to_dict() for p in self.procesos]
        RUTA.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------------
    # Funciones de apoyo (empiezan con _ porque solo se usan aquí dentro)
    # ------------------------------------------------------------------

    def _buscar(self, pid):
        # Devuelve el proceso con ese pid o lanza un error si no existe.
        for p in self.procesos:
            if p.pid == pid:
                return p
        raise ValueError(f"No existe un proceso con PID {pid}")

    def _en_ejecucion(self):
        # Devuelve el proceso que tiene el CPU, o None si el CPU está libre.
        # Se simula un solo CPU, así que solo puede haber uno.
        for p in self.procesos:
            if p.estado == EN_EJECUCION:
                return p
        return None

    def _cambiar(self, proceso, nuevo_estado):
        # ÚNICO lugar donde se cambia un estado. Revisa la tabla de transiciones.
        permitidos = TRANSICIONES[proceso.estado]
        if nuevo_estado not in permitidos:
            raise ValueError(
                f"{proceso.nombre} (PID {proceso.pid}) no puede pasar de "
                f"'{proceso.estado}' a '{nuevo_estado}'"
            )
        proceso.cambiar_estado(nuevo_estado)

    def _terminar(self, proceso):
        # Al terminar, el sistema libera los recursos del proceso.
        self._cambiar(proceso, TERMINADO)
        proceso.archivos_abiertos = []
        proceso.dispositivos = []

    # ------------------------------------------------------------------
    # Acciones que usa la interfaz (nombres acordados en el README)
    # ------------------------------------------------------------------

    def listar(self):
        # Devuelve diccionarios en lugar de los objetos, así la interfaz
        # puede leer los datos del BCP pero no modificarlos por accidente.
        return [p.to_dict() for p in self.procesos]

    def crear(self, nombre, prioridad, memoria_mb):
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del proceso no puede estar vacío")
        if prioridad < 0:
            raise ValueError("La prioridad no puede ser negativa")
        if memoria_mb <= 0:
            raise ValueError("La memoria debe ser mayor que 0 MB")

        # El nuevo PID es el mayor que exista + 1 (igual que en la versión de consola).
        nuevo_pid = max((p.pid for p in self.procesos), default=0) + 1

        proceso = Proceso(
            nuevo_pid,
            nombre,
            prioridad,
            memoria_mb,
            # Cada proceso dura un número distinto de pulsos.
            tiempo_restante=random.randint(5, 15),
        )
        self.procesos.append(proceso)
        self.guardar()
        return proceso.to_dict()

    def ejecutar(self, pid):
        # Le da el CPU a este proceso. Si otro lo tenía, ese vuelve a Listo.
        proceso = self._buscar(pid)
        if proceso.estado == EN_EJECUCION:
            raise ValueError(f"{proceso.nombre} ya está en ejecución")
        if proceso.estado == TERMINADO:
            raise ValueError(f"{proceso.nombre} ya terminó y no se puede ejecutar")

        # Para llegar a En ejecución primero tiene que estar Listo,
        # así que se pasa por Listo si venía de Nuevo o En espera.
        if proceso.estado in (NUEVO, EN_ESPERA):
            self._cambiar(proceso, LISTO)

        actual = self._en_ejecucion()
        if actual is not None:
            self._cambiar(actual, LISTO)

        self._cambiar(proceso, EN_EJECUCION)
        self.guardar()
        return proceso.to_dict()

    def pausar(self, pid):
        # Solo se puede pausar el proceso que tiene el CPU.
        # Queda En espera hasta que alguien lo vuelva a ejecutar.
        proceso = self._buscar(pid)
        if proceso.estado != EN_EJECUCION:
            raise ValueError(
                f"Solo se puede pausar un proceso en ejecución "
                f"({proceso.nombre} está '{proceso.estado}')"
            )
        self._cambiar(proceso, EN_ESPERA)
        self.guardar()
        return proceso.to_dict()

    def detener(self, pid):
        # Termina el proceso en cualquier estado (como "Finalizar tarea").
        proceso = self._buscar(pid)
        if proceso.estado == TERMINADO:
            raise ValueError(f"{proceso.nombre} ya está terminado")
        self._terminar(proceso)
        self.guardar()
        return proceso.to_dict()

    def pulso(self):
        # Un "tic" del reloj. app.py lo llama cada cierto tiempo con after().
        # Aquí NO se usa sleep: cada llamada avanza un solo paso.

        # 1. Admitir: los procesos Nuevos pasan a Listo.
        for p in self.procesos:
            if p.estado == NUEVO:
                self._cambiar(p, LISTO)

        # 2. Si el CPU está libre, el planificador elige al siguiente.
        #    Número de prioridad MÁS BAJO = MÁS importante (como en Linux).
        #    Si empatan, gana el PID más bajo (el que llegó primero).
        actual = self._en_ejecucion()
        if actual is None:
            listos = [p for p in self.procesos if p.estado == LISTO]
            if listos:
                actual = min(listos, key=lambda p: (p.prioridad, p.pid))
                self._cambiar(actual, EN_EJECUCION)

        # 3. El proceso en ejecución avanza una instrucción.
        if actual is not None:
            actual.tiempo_cpu += 1
            actual.tiempo_restante -= 1
            actual.contador_programa += 4  # cada instrucción ocupa 4 bytes
            # Los registros cambian como si el CPU estuviera calculando algo.
            for nombre_registro in actual.registros:
                actual.registros[nombre_registro] = random.randint(0, 255)

            # 4. Si ya no le queda tiempo, termina y libera el CPU.
            if actual.tiempo_restante <= 0:
                self._terminar(actual)

        self.guardar()
