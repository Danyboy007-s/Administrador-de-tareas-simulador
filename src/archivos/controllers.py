# Lógica del sistema de archivos simulado: rutas, permisos y operaciones.
# La interfaz NO cambia los elementos directamente: llama a estas funciones
# y muestra lo que devuelven. Si algo no se permite se lanza un error con un
# mensaje que la interfaz muestra en un messagebox:
#   ValueError        -> dato no válido (nombre vacío, tipo incorrecto...)
#   PermissionError   -> falta un permiso (lectura, escritura o ejecución)
#   FileNotFoundError -> la ruta no existe
# Nada de esto toca archivos reales: todo vive en memoria y en data/archivos.json.

import json
from pathlib import Path

from src.archivos.models import ARCHIVO, CARPETA, PERMISOS, TIPOS, Elemento, ahora

# Ruta del JSON a partir de la ubicación de ESTE archivo (igual que en procesos).
RUTA = Path(__file__).resolve().parents[2] / "data" / "archivos.json"

# Estructura que aparece la primera vez, cuando el JSON está vacío.
# Imita las carpetas típicas de Linux.
# (ruta de la carpeta padre, nombre, tipo, contenido)
ELEMENTOS_EJEMPLO = [
    ("/", "home", CARPETA, ""),
    ("/home", "usuario", CARPETA, ""),
    ("/home/usuario", "documentos", CARPETA, ""),
    ("/home/usuario/documentos", "notas.txt", ARCHIVO, "Notas de ejemplo del sistema simulado."),
    ("/home/usuario", "bienvenida.txt", ARCHIVO, "Bienvenido al sistema de archivos simulado."),
    ("/home/usuario", "script.sh", ARCHIVO, "echo 'Hola desde un script simulado'"),
    ("/", "etc", CARPETA, ""),
    ("/etc", "hostname", ARCHIVO, "simulador"),
]

# Carpeta donde se "instalan" los programas (como Archivos de programa en
# Windows o /usr/bin en Linux). Al ejecutar uno aparece en el administrador
# de tareas y consume memoria según su tamaño.
CARPETA_PROGRAMAS = "/programas"
# (nombre, tamaño en MB)
PROGRAMAS_INSTALADOS = [
    ("roblox", 1500),
    ("minecraft", 1100),
    ("firefox", 450),
    ("vscode", 380),
    ("editor_texto", 40),
    ("calculadora", 15),
]
MB = 1024 * 1024


class SistemaArchivos:
    def __init__(self):
        self.raiz = self.cargar()
        if self.raiz is None:
            self.raiz = Elemento("/", CARPETA)
            for ruta, nombre, tipo, contenido in ELEMENTOS_EJEMPLO:
                self.crear(ruta, nombre, tipo)
                if contenido:
                    self.modificar(f"{ruta.rstrip('/')}/{nombre}", contenido)
            # El script de ejemplo se puede ejecutar (rwx).
            script = self._buscar("/home/usuario/script.sh")
            script.permisos["ejecucion"] = True
            self.guardar()
        self._asegurar_programas()

    def _asegurar_programas(self):
        # Si no existe /programas (primera vez o datos de una versión anterior),
        # se crea con los programas de ejemplo ya instalados.
        if self.raiz.buscar_hijo(CARPETA_PROGRAMAS.strip("/")) is not None:
            return
        self.crear("/", CARPETA_PROGRAMAS.strip("/"), CARPETA)
        for nombre, tamano_mb in PROGRAMAS_INSTALADOS:
            self.instalar(nombre, tamano_mb)

    # ------------------------------------------------------------------
    # Guardar y cargar
    # ------------------------------------------------------------------

    def cargar(self):
        # Devuelve la carpeta raíz con todo el árbol, o None si no hay datos.
        if not RUTA.exists():
            return None
        texto = RUTA.read_text(encoding="utf-8").strip()
        if not texto:
            return None
        try:
            raiz = Elemento.from_dict(json.loads(texto))
            if not raiz.es_carpeta():
                raise ValueError("la raíz no es una carpeta")
            return raiz
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            # El JSON está dañado (por ejemplo, se editó a mano). En vez de que
            # el programa no arranque, se guarda una copia del archivo malo y
            # se empieza con los datos de ejemplo.
            respaldo = RUTA.with_name(RUTA.name + ".danado")
            RUTA.replace(respaldo)
            print(f"Aviso: {RUTA.name} estaba dañado ({error}); se guardó como {respaldo.name}")
            return None

    def guardar(self):
        # Basta con guardar la raíz: to_dict() recorre todo el árbol.
        # La carpeta data/ se crea si no existe (los JSON no se suben a Git).
        RUTA.parent.mkdir(exist_ok=True)
        RUTA.write_text(
            json.dumps(self.raiz.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Funciones de apoyo
    # ------------------------------------------------------------------

    @staticmethod
    def _partes(ruta):
        # "/home/usuario/" -> ["home", "usuario"]. La raíz "/" -> [].
        # Se ignoran "." y las partes vacías; ".." sube un nivel.
        partes = []
        for parte in str(ruta or "/").split("/"):
            if parte in ("", "."):
                continue
            if parte == "..":
                if partes:
                    partes.pop()
            else:
                partes.append(parte)
        return partes

    def _buscar(self, ruta):
        # Recorre la ruta desde la raíz y devuelve el Elemento final.
        # Para pasar por una carpeta hace falta permiso de EJECUCIÓN en ella,
        # igual que en Linux (sin "x" no puedes entrar con cd).
        actual = self.raiz
        recorrido = ""
        for parte in self._partes(ruta):
            if not actual.es_carpeta():
                raise FileNotFoundError(f"'{recorrido}' es un archivo, no una carpeta")
            if not actual.tiene_permiso("ejecucion"):
                raise PermissionError(
                    f"Sin permiso de ejecución en '{recorrido or '/'}': no se puede entrar"
                )
            siguiente = actual.buscar_hijo(parte)
            recorrido += "/" + parte
            if siguiente is None:
                raise FileNotFoundError(f"No existe '{recorrido}'")
            actual = siguiente
        return actual

    def _buscar_padre(self, ruta):
        # Devuelve (carpeta padre, nombre del elemento) de una ruta.
        partes = self._partes(ruta)
        if not partes:
            raise ValueError("La raíz '/' no tiene carpeta padre")
        padre = self._buscar("/" + "/".join(partes[:-1]))
        return padre, partes[-1]

    @staticmethod
    def _exigir(elemento, permiso, accion):
        # ÚNICO lugar donde se revisan los permisos de una acción.
        if not elemento.tiene_permiso(permiso):
            # La clave no lleva acento (como en el JSON), el mensaje sí.
            nombre_permiso = "ejecución" if permiso == "ejecucion" else permiso
            raise PermissionError(
                f"No se puede {accion} '{elemento.nombre}': falta permiso de {nombre_permiso}"
            )

    # ------------------------------------------------------------------
    # Acciones que usa la interfaz (nombres acordados en el README)
    # ------------------------------------------------------------------

    def listar(self, ruta):
        # Abrir una carpeta es como "cd" + "ls" en Linux:
        #   cd necesita permiso de EJECUCIÓN y ls necesita permiso de LECTURA.
        # Devuelve diccionarios (sin los hijos de cada uno) para que la
        # interfaz no pueda modificar el árbol por accidente.
        carpeta = self._buscar(ruta)
        if not carpeta.es_carpeta():
            raise ValueError(f"'{carpeta.nombre}' no es una carpeta")
        self._exigir(carpeta, "ejecucion", "entrar a")
        self._exigir(carpeta, "lectura", "listar")
        # Primero carpetas y luego archivos, cada grupo en orden alfabético.
        hijos = sorted(carpeta.hijos, key=lambda e: (not e.es_carpeta(), e.nombre.lower()))
        return [{**h.to_dict(), "hijos": []} for h in hijos]

    def crear(self, ruta, nombre, tipo):
        # Crear dentro de una carpeta necesita permiso de ESCRITURA en ella.
        padre = self._buscar(ruta)
        if not padre.es_carpeta():
            raise ValueError("Solo se pueden crear elementos dentro de una carpeta")
        self._exigir(padre, "escritura", "crear en")

        nombre = nombre.strip()
        if not nombre or nombre in (".", "..") or "/" in nombre:
            raise ValueError("Nombre no válido: no puede estar vacío ni tener '/'")
        if tipo not in TIPOS:
            raise ValueError(f"Tipo no válido: {tipo}")
        if padre.buscar_hijo(nombre) is not None:
            raise ValueError(f"Ya existe '{nombre}' en esta carpeta")

        nuevo = Elemento(nombre, tipo)
        padre.hijos.append(nuevo)
        padre.modificado = nuevo.creado
        self.guardar()
        return nuevo.to_dict()

    def leer(self, ruta):
        # Leer un archivo necesita permiso de LECTURA en el archivo.
        elemento = self._buscar(ruta)
        if elemento.es_carpeta():
            raise ValueError(f"'{elemento.nombre}' es una carpeta; ábrela para ver su contenido")
        self._exigir(elemento, "lectura", "leer")
        return elemento.contenido

    def modificar(self, ruta, contenido):
        # Modificar un archivo necesita permiso de ESCRITURA en el archivo.
        elemento = self._buscar(ruta)
        if elemento.es_carpeta():
            raise ValueError("Solo se puede modificar el contenido de un archivo")
        self._exigir(elemento, "escritura", "modificar")
        elemento.contenido = str(contenido)
        elemento.tamano = elemento.calcular_tamano()
        elemento.modificado = ahora()
        self.guardar()
        return elemento.to_dict()

    def eliminar(self, ruta):
        # Eliminar necesita permiso de ESCRITURA en la carpeta PADRE, no en el
        # elemento (en Linux pasa igual: borrar es cambiar la carpeta que lo contiene).
        padre, nombre = self._buscar_padre(ruta)
        self._exigir(padre, "escritura", "eliminar en")
        elemento = padre.buscar_hijo(nombre)
        if elemento is None:
            raise FileNotFoundError(f"No existe '{nombre}'")
        padre.hijos.remove(elemento)
        padre.modificado = ahora()
        self.guardar()
        return elemento.to_dict()

    def instalar(self, nombre, tamano_mb):
        # Simula instalar un programa: crea un archivo ejecutable en
        # /programas con el tamaño indicado. No se descarga nada real.
        if not isinstance(tamano_mb, int) or tamano_mb <= 0:
            raise ValueError("El tamaño debe ser un número entero de MB mayor que 0")
        if self.raiz.buscar_hijo(CARPETA_PROGRAMAS.strip("/")) is None:
            self.crear("/", CARPETA_PROGRAMAS.strip("/"), CARPETA)
        self.crear(CARPETA_PROGRAMAS, nombre, ARCHIVO)  # valida nombre y permisos
        programa = self._buscar(f"{CARPETA_PROGRAMAS}/{nombre.strip()}")
        programa.contenido = (
            f"Programa simulado: {programa.nombre}\n"
            f"Tamaño de instalación: {tamano_mb} MB\n"
            "Usa el botón Ejecutar para abrirlo en el administrador de tareas."
        )
        # El tamaño es el del programa instalado, no el del texto de arriba.
        programa.tamano = tamano_mb * MB
        # r-x: se puede leer y ejecutar, pero no modificar (como en /usr/bin).
        programa.permisos = {"lectura": True, "escritura": False, "ejecucion": True}
        self.guardar()
        return programa.to_dict()

    def ejecutar(self, ruta):
        # Ejecutar un archivo necesita permiso de EJECUCIÓN en el archivo.
        # Este módulo no crea el proceso (procesos/ y archivos/ no se importan
        # entre sí): solo revisa el permiso y devuelve los datos del archivo.
        # app.py es quien le pide al administrador de procesos que lo cree.
        elemento = self._buscar(ruta)
        if elemento.es_carpeta():
            raise ValueError(f"'{elemento.nombre}' es una carpeta; no se puede ejecutar")
        self._exigir(elemento, "ejecucion", "ejecutar")
        return elemento.to_dict()

    def cambiar_permisos(self, ruta, permisos):
        # Como chmod: el dueño siempre puede cambiar los permisos, aunque
        # se haya quitado a sí mismo la lectura o la escritura.
        elemento = self._buscar(ruta)
        faltan = [p for p in PERMISOS if p not in permisos]
        if faltan:
            raise ValueError(f"Faltan permisos por indicar: {', '.join(faltan)}")
        elemento.permisos = {p: bool(permisos[p]) for p in PERMISOS}
        elemento.modificado = ahora()
        self.guardar()
        return elemento.to_dict()
