# Modelo de un elemento del sistema de archivos simulado: un archivo o una carpeta.
# Este archivo solo guarda datos. Las reglas (qué permiso pide cada acción,
# cómo se recorre una ruta) van en controllers.py.

from datetime import datetime

# Constantes de los dos tipos de elemento.
# La interfaz compara estos textos, así que deben escribirse igual en todos lados.
ARCHIVO = "archivo"
CARPETA = "carpeta"
TIPOS = (ARCHIVO, CARPETA)

# Los tres permisos de un elemento (como rwx en Linux).
#   lectura   (r): ver el contenido de un archivo o listar una carpeta
#   escritura (w): cambiar un archivo, o crear/eliminar dentro de una carpeta
#   ejecucion (x): ejecutar un archivo, o entrar a una carpeta
PERMISOS = ("lectura", "escritura", "ejecucion")


def ahora():
    # Fecha y hora actual como texto, para guardarla directo en el JSON.
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class Elemento:
    # Se usa UNA sola clase para archivos y carpetas porque comparten casi
    # todos los datos. Lo que cambia es el campo tipo:
    #   - un archivo usa contenido
    #   - una carpeta usa hijos (lista de otros Elemento) -> forma un árbol
    def __init__(
        self,
        nombre,
        tipo,
        contenido="",
        permisos=None,   # diccionario {lectura, escritura, ejecucion}
        hijos=None,      # lista de Elemento (solo carpetas)
        creado=None,     # fecha de creación como texto
        modificado=None, # fecha de la última modificación
        tamano=None,     # bytes; si no llega se calcula
    ):
        if tipo not in TIPOS:
            raise ValueError(f"Tipo no válido: {tipo}")

        self.nombre = nombre
        self.tipo = tipo
        self.contenido = contenido

        # Igual que en Proceso: listas y diccionarios llegan como None y se
        # crean aquí, para que cada elemento tenga los suyos.
        if permisos is None:
            # Valores típicos de Linux: un archivo nuevo es rw-, una carpeta rwx.
            permisos = {
                "lectura": True,
                "escritura": True,
                "ejecucion": tipo == CARPETA,
            }
        self.permisos = permisos

        if hijos is None:
            hijos = []
        self.hijos = hijos

        if creado is None:
            creado = ahora()
        self.creado = creado
        self.modificado = modificado if modificado is not None else creado

        if tamano is None:
            tamano = self.calcular_tamano()
        self.tamano = tamano

    def es_carpeta(self):
        return self.tipo == CARPETA

    def tiene_permiso(self, permiso):
        # Devuelve True o False. La decisión de bloquear la acción la toma
        # el controlador, no el modelo.
        return bool(self.permisos.get(permiso, False))

    def calcular_tamano(self):
        # Un archivo ocupa los bytes de su contenido. Se usa encode("utf-8")
        # porque letras como "ñ" o "á" ocupan 2 bytes, igual que en un disco real.
        if self.es_carpeta():
            return 0
        return len(self.contenido.encode("utf-8"))

    def buscar_hijo(self, nombre):
        # Devuelve el hijo con ese nombre, o None si no existe.
        for hijo in self.hijos:
            if hijo.nombre == nombre:
                return hijo
        return None

    def to_dict(self):
        # Convierte el elemento en diccionario para el JSON o la interfaz.
        # Los hijos también son Elemento, así que cada uno se convierte con
        # su propio to_dict(). Esto es RECURSIÓN: recorre todo el árbol y se
        # detiene sola cuando llega a un elemento sin hijos.
        return {
            "nombre": self.nombre,
            "tipo": self.tipo,
            "tamano": self.tamano,
            "creado": self.creado,
            "modificado": self.modificado,
            "permisos": dict(self.permisos),
            "contenido": self.contenido,
            "hijos": [hijo.to_dict() for hijo in self.hijos],
        }

    @classmethod
    def from_dict(cls, datos):
        # Lo contrario de to_dict. A diferencia de Proceso, aquí NO basta con
        # cls(**datos): los hijos llegan como diccionarios y hay que
        # convertir cada uno en Elemento (también de forma recursiva).
        # Solo se usan los campos conocidos; si el JSON trae otros, se ignoran.
        campos = ("nombre", "tipo", "contenido", "permisos", "creado", "modificado", "tamano")
        datos_limpios = {clave: datos[clave] for clave in campos if clave in datos}
        datos_limpios["hijos"] = [cls.from_dict(h) for h in datos.get("hijos", [])]
        return cls(**datos_limpios)

    def __repr__(self):
        return f"Elemento(nombre={self.nombre!r}, tipo={self.tipo!r}, hijos={len(self.hijos)})"
