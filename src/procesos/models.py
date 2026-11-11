# Modelo de un proceso simulado y los datos de su BCP (Bloque de Control de Proceso).
# Este archivo solo guarda datos. Las reglas (qué cambio de estado se permite,
# qué hace cada pulso del reloj) van en controllers.py.

# Constantes de los 5 estados de un proceso.
# Usar constantes evita errores de escritura como "En ejecucion" sin acento.
NUEVO = "Nuevo"
LISTO = "Listo"
EN_EJECUCION = "En ejecución"
EN_ESPERA = "En espera"
TERMINADO = "Terminado"

# Tupla con todos los estados. Sirve para validar y para que el controlador
# o la interfaz puedan recorrerlos sin repetir la lista.
ESTADOS = (NUEVO, LISTO, EN_EJECUCION, EN_ESPERA, TERMINADO)


class Proceso:
    # Cada atributo es un campo del BCP. Los nombres son los acordados en el README.
    #
    # Solo pid, nombre, prioridad y memoria_mb son obligatorios porque son los que
    # recibe crear() del controlador (el pid lo calcula el controlador).
    # Los demás tienen un valor inicial para un proceso recién creado,
    # pero se pueden pasar al cargar un proceso desde el JSON.
    def __init__(
        self,
        pid,
        nombre,
        prioridad,
        memoria_mb,
        ppid=0,                 # PID del proceso padre; 0 = lo creó el sistema
        usuario="root",         # dueño del proceso
        estado=NUEVO,           # todo proceso nace en estado Nuevo
        contador_programa=0,    # dirección de la siguiente instrucción a ejecutar
        registros=None,         # valores de los registros del CPU (diccionario)
        tiempo_cpu=0,           # pulsos que ya lleva usando el CPU
        tiempo_restante=10,     # pulsos que le faltan para terminar
        archivos_abiertos=None, # lista de nombres de archivos que usa
        dispositivos=None,      # lista de dispositivos de E/S asignados
    ):
        # Identificación del proceso
        self.pid = pid
        self.ppid = ppid
        self.nombre = nombre
        self.usuario = usuario

        # Estado y planificación
        self.estado = estado
        self.prioridad = prioridad

        # Contexto del CPU: lo que se guarda para poder pausar y reanudar
        self.contador_programa = contador_programa
        # Las listas y diccionarios llegan como None y se crean aquí.
        # Si se pusiera registros={} en la firma, TODOS los procesos
        # compartirían el mismo diccionario.
        if registros is None:
            registros = {"AX": 0, "BX": 0, "CX": 0, "DX": 0}
        self.registros = registros

        # Contabilidad del tiempo
        self.tiempo_cpu = tiempo_cpu
        self.tiempo_restante = tiempo_restante

        # Recursos asignados
        self.memoria_mb = memoria_mb
        if archivos_abiertos is None:
            archivos_abiertos = []
        self.archivos_abiertos = archivos_abiertos
        if dispositivos is None:
            dispositivos = []
        self.dispositivos = dispositivos

    def cambiar_estado(self, nuevo_estado):
        # Solo revisa que el estado exista.
        # Qué saltos están permitidos (por ejemplo, Terminado -> Listo no)
        # lo decide la tabla de transiciones en controllers.py.
        if nuevo_estado not in ESTADOS:
            raise ValueError(f"Estado no válido: {nuevo_estado}")
        self.estado = nuevo_estado

    def to_dict(self):
        # Convierte el proceso en un diccionario para guardarlo en JSON
        # o para que la interfaz muestre sus datos.
        return {
            "pid": self.pid,
            "ppid": self.ppid,
            "nombre": self.nombre,
            "usuario": self.usuario,
            "estado": self.estado,
            "contador_programa": self.contador_programa,
            "registros": self.registros,
            "prioridad": self.prioridad,
            "tiempo_cpu": self.tiempo_cpu,
            "tiempo_restante": self.tiempo_restante,
            "memoria_mb": self.memoria_mb,
            "archivos_abiertos": self.archivos_abiertos,
            "dispositivos": self.dispositivos,
        }

    @classmethod
    def from_dict(cls, datos):
        # Hace lo contrario de to_dict: crea un Proceso a partir de un diccionario
        # leído del JSON. Las claves del diccionario tienen los mismos nombres
        # que los parámetros de __init__, así que ** las pasa todas de una vez.
        # Así se recupera TODO, incluido el estado.
        return cls(**datos)

    def __repr__(self):
        # Texto que se ve al hacer print(proceso). Útil para probar en consola.
        return f"Proceso(pid={self.pid}, nombre={self.nombre!r}, estado={self.estado!r})"
