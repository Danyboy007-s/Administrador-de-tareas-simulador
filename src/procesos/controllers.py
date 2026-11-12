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
#   Listo -> En espera        (se pausa mientras espera su turno, como kill -STOP)
#   En espera -> Listo        (se reanuda)
#   Cualquiera -> Terminado   (termina o se detiene)
# Terminado no puede pasar a ningún otro estado: para volver a abrir el
# programa se crea un proceso NUEVO con otro PID (ver relanzar).
TRANSICIONES = {
    NUEVO: (LISTO, TERMINADO),
    LISTO: (EN_EJECUCION, EN_ESPERA, TERMINADO),
    EN_EJECUCION: (LISTO, EN_ESPERA, TERMINADO),
    EN_ESPERA: (LISTO, TERMINADO),
    TERMINADO: (),
}

# Procesos CRÍTICOS del sistema. Arrancan con el programa, nunca terminan
# solos y, si el usuario los detiene, el sistema se apaga (como System32 en
# Windows o el kernel en Linux).
# (nombre, prioridad, memoria_mb)
PROCESOS_SISTEMA = [
    ("systemd", 0, 12),  # primer proceso del sistema (PID 1), padre de todos
    ("Xorg", 1, 85),     # servidor gráfico: dibuja las ventanas
]

# Límites de memoria para clasificar el consumo de un proceso.
CONSUMO_ALTO_MB = 1000   # 1000 MB o más  -> Alto  (rojo)
CONSUMO_MEDIO_MB = 300   # 300 a 999 MB   -> Medio (amarillo); menos -> Bajo (verde)


def nivel_consumo(memoria_mb):
    # Clasifica el consumo con límites fijos para que sea fácil de explicar.
    if memoria_mb >= CONSUMO_ALTO_MB:
        return "Alto"
    if memoria_mb >= CONSUMO_MEDIO_MB:
        return "Medio"
    return "Bajo"


class AdministradorProcesos:
    def __init__(self):
        # Turno de llegada a la cola de Listos de cada PID (round robin).
        # No es parte del BCP: es información del planificador.
        self._turnos = {}
        self._siguiente_turno = 0
        # Pulsos que lleva el proceso actual en el CPU sin soltarlo.
        self._pulsos_en_cpu = 0

        # Abrir el programa es como ENCENDER el equipo: los procesos de la
        # sesión anterior ya no existen y arrancan los del sistema.
        self.procesos = []
        for nombre, prioridad, memoria in PROCESOS_SISTEMA:
            self.crear(nombre, prioridad, memoria, critico=True)

    # ------------------------------------------------------------------
    # Guardar y cargar
    # ------------------------------------------------------------------

    def guardar(self):
        # El JSON es una "foto" de los procesos de la sesión actual (parecido
        # a /proc en Linux). No se vuelve a cargar al iniciar, porque al
        # encender un equipo ningún proceso anterior sigue vivo.
        datos = [p.to_dict() for p in self.procesos]
        # La carpeta data/ se crea si no existe (los JSON no se suben a Git).
        RUTA.parent.mkdir(exist_ok=True)
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
        if nuevo_estado == LISTO:
            # Entra al final de la cola de Listos.
            self._formar(proceso)
        elif nuevo_estado == EN_EJECUCION:
            # Empieza un turno nuevo en el CPU.
            self._pulsos_en_cpu = 0

    def _despachar(self):
        # Planificador ROUND ROBIN: si el CPU está libre, se lo da al proceso
        # que lleva más tiempo esperando en la cola de Listos (turno más bajo).
        # Devuelve el proceso que queda con el CPU, o None si no hay ninguno.
        actual = self._en_ejecucion()
        if actual is None:
            listos = [p for p in self.procesos if p.estado == LISTO]
            if listos:
                actual = min(listos, key=lambda p: self._turnos.get(p.pid, 0))
                self._cambiar(actual, EN_EJECUCION)
        return actual

    def _formar(self, proceso):
        # Le da al proceso el siguiente número de turno en la cola.
        self._turnos[proceso.pid] = self._siguiente_turno
        self._siguiente_turno += 1

    @staticmethod
    def _quantum(proceso):
        # Pulsos seguidos que un proceso puede usar el CPU antes de ceder el
        # turno. Mejor prioridad (número más bajo) = turno más largo:
        #   prioridad 0 -> 6 pulsos ... prioridad 10 -> 1 pulso
        return 1 + (10 - proceso.prioridad) // 2

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
        # Además del BCP se agrega "consumo" (Alto, Medio o Bajo) para que la
        # interfaz no tenga que decidir la regla. Un proceso Terminado ya
        # liberó su memoria, así que no consume.
        return [
            {**p.to_dict(), "consumo": "—" if p.estado == TERMINADO else nivel_consumo(p.memoria_mb)}
            for p in self.procesos
        ]

    def crear(self, nombre, prioridad, memoria_mb, archivos_abiertos=None, critico=False):
        # archivos_abiertos es opcional: lo usa app.py cuando un proceso nace
        # al ejecutar un archivo del sistema de archivos simulado.
        # critico solo lo usa el propio controlador al encender el sistema.
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del proceso no puede estar vacío")
        # Rango acordado en el README: 0 es la más importante y 10 la menos.
        if not 0 <= prioridad <= 10:
            raise ValueError("La prioridad debe estar entre 0 y 10")
        if memoria_mb <= 0:
            raise ValueError("La memoria debe ser mayor que 0 MB")

        # El nuevo PID es el mayor que exista + 1 (igual que en la versión de consola).
        nuevo_pid = max((p.pid for p in self.procesos), default=0) + 1

        proceso = Proceso(
            nuevo_pid,
            nombre,
            prioridad,
            memoria_mb,
            # Los procesos del sistema son de root e hijos de nadie (ppid 0);
            # los demás son del usuario e hijos de systemd (PID 1).
            ppid=0 if critico else 1,
            usuario="root" if critico else "usuario",
            # Los críticos nunca terminan solos (None). Los demás duran un
            # número distinto de pulsos (segundos de CPU).
            tiempo_restante=None if critico else random.randint(20, 60),
            archivos_abiertos=list(archivos_abiertos or []),
            critico=critico,
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
            raise ValueError(
                f"{proceso.nombre} ya terminó y no se puede ejecutar; "
                "ábrelo de nuevo como un proceso nuevo"
            )

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
        # Se puede pausar un proceso activo: el que tiene el CPU o uno que
        # espera su turno (Listo). Queda En espera y el planificador no le da
        # el CPU hasta que alguien lo vuelva a ejecutar.
        proceso = self._buscar(pid)
        if proceso.estado == EN_ESPERA:
            raise ValueError(f"{proceso.nombre} ya está en pausa (En espera)")
        if proceso.estado == TERMINADO:
            raise ValueError(f"{proceso.nombre} ya terminó; no se puede pausar")
        if proceso.estado == NUEVO:
            # Primero el sistema lo admite y luego se pausa.
            self._cambiar(proceso, LISTO)
        self._cambiar(proceso, EN_ESPERA)
        self.guardar()
        return proceso.to_dict()

    def relanzar(self, pid):
        # Vuelve a abrir un programa que ya terminó. El proceso terminado NO
        # revive: se crea uno NUEVO (otro PID) con el mismo nombre, prioridad
        # y memoria, como al abrir otra vez una aplicación que cerraste.
        proceso = self._buscar(pid)
        if proceso.estado != TERMINADO:
            raise ValueError(f"{proceso.nombre} sigue activo; no hace falta abrirlo de nuevo")
        if proceso.critico:
            raise ValueError("Los procesos del sistema solo arrancan al encender el equipo")
        return self.crear(proceso.nombre, proceso.prioridad, proceso.memoria_mb)

    def detener(self, pid):
        # Termina el proceso en cualquier estado (como "Finalizar tarea").
        # Si es crítico también se permite; el dict devuelto trae
        # critico=True y app.py se encarga de "apagar" el sistema.
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
        actual = self._despachar()

        # 3. El proceso en ejecución avanza una instrucción.
        if actual is not None:
            actual.tiempo_cpu += 1
            if actual.tiempo_restante is not None:  # None = proceso del sistema
                actual.tiempo_restante -= 1
            actual.contador_programa += 4  # cada instrucción ocupa 4 bytes
            self._pulsos_en_cpu += 1
            # Los registros cambian como si el CPU estuviera calculando algo.
            for nombre_registro in actual.registros:
                actual.registros[nombre_registro] = random.randint(0, 255)

            # 4. Si ya no le queda tiempo, termina y libera el CPU.
            if actual.tiempo_restante is not None and actual.tiempo_restante <= 0:
                self._terminar(actual)
            # 5. Si ya usó su quantum y hay otros esperando, cede el CPU y
            #    vuelve al final de la cola (cambio de contexto). Su BCP guarda
            #    el contador de programa y los registros para continuar después.
            elif self._pulsos_en_cpu >= self._quantum(actual) and any(
                p.estado == LISTO for p in self.procesos
            ):
                self._cambiar(actual, LISTO)

        # 6. Si el CPU quedó libre, se le da enseguida al siguiente. Así entre
        #    un pulso y otro siempre se ve quién tiene el CPU, y un proceso
        #    con quantum de 1 pulso también aparece "En ejecución".
        self._despachar()

        self.guardar()
