"""Punto de entrada gráfico del simulador.

Los controladores de demostración conservan los datos únicamente en memoria.
Cuando estén disponibles los controladores de src.procesos y src.archivos, se
pueden sustituir estas clases sin cambiar las ventanas de views.py.
"""

from __future__ import annotations

import copy
import posixpath
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from typing import Any

from views import PROCESOS_EJEMPLO, SISTEMA_ARCHIVOS_EJEMPLO, VentanaArchivos, VentanaProcesos


class ControladorProcesosDemo:
    """Implementación en memoria de la interfaz acordada para procesos."""

    def __init__(self) -> None:
        self._procesos = copy.deepcopy(PROCESOS_EJEMPLO)
        self._siguiente_pid = max((proceso["pid"] for proceso in self._procesos), default=100) + 1

    def listar(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._procesos)

    def crear(self, nombre: str, prioridad: int, memoria_mb: int) -> dict[str, Any]:
        nombre = nombre.strip()
        if not nombre:
            raise ValueError("El nombre del proceso no puede estar vacío.")
        if not 1 <= int(prioridad) <= 10:
            raise ValueError("La prioridad debe estar entre 1 y 10.")
        if int(memoria_mb) < 1:
            raise ValueError("La memoria debe ser mayor que cero.")
        proceso = {
            "pid": self._siguiente_pid,
            "ppid": 1,
            "nombre": nombre,
            "usuario": "usuario",
            "estado": "Nuevo",
            "contador_programa": 0,
            "registros": {"AX": "0000", "BX": "0000", "CX": "0000", "DX": "0000"},
            "prioridad": int(prioridad),
            "tiempo_cpu": 0,
            "tiempo_restante": 10,
            "memoria_mb": int(memoria_mb),
            "archivos_abiertos": [],
            "dispositivos": [],
        }
        self._siguiente_pid += 1
        self._procesos.append(proceso)
        return copy.deepcopy(proceso)

    def ejecutar(self, pid: int) -> str:
        proceso = self._buscar(pid)
        if proceso["estado"] not in ("Nuevo", "Listo", "En espera"):
            raise ValueError(f"No se puede ejecutar un proceso en estado «{proceso['estado']}».")
        for otro in self._procesos:
            if otro["estado"] == "En ejecución":
                otro["estado"] = "Listo"
        proceso["estado"] = "En ejecución"
        return f"Proceso {pid} en ejecución"

    def pausar(self, pid: int) -> str:
        proceso = self._buscar(pid)
        if proceso["estado"] != "En ejecución":
            raise ValueError("Solo se puede pausar un proceso en ejecución.")
        proceso["estado"] = "En espera"
        return f"Proceso {pid} en espera"

    def detener(self, pid: int) -> str:
        proceso = self._buscar(pid)
        proceso["estado"] = "Terminado"
        return f"Proceso {pid} terminado"

    def pulso(self) -> None:
        """Avanza un segundo simulado sin bloquear la interfaz."""
        for proceso in self._procesos:
            if proceso["estado"] == "Nuevo":
                proceso["estado"] = "Listo"
            elif proceso["estado"] == "En ejecución":
                proceso["contador_programa"] += 1
                proceso["tiempo_cpu"] += 1
                proceso["tiempo_restante"] = max(0, proceso["tiempo_restante"] - 1)
                if proceso["tiempo_restante"] == 0:
                    proceso["estado"] = "Terminado"

    def _buscar(self, pid: int) -> dict[str, Any]:
        for proceso in self._procesos:
            if proceso["pid"] == int(pid):
                return proceso
        raise KeyError(f"No existe el proceso con PID {pid}.")


class ControladorArchivosDemo:
    """Sistema de archivos virtual en memoria; nunca toca el disco real."""

    def __init__(self) -> None:
        self._raiz = {
            "nombre": "/",
            "tipo": "carpeta",
            "tamano": 0,
            "creado": "2026-11-11 09:00",
            "modificado": "2026-11-11 09:00",
            "permisos": {"lectura": True, "escritura": True, "ejecucion": True},
            "contenido": "",
            "hijos": copy.deepcopy(SISTEMA_ARCHIVOS_EJEMPLO),
        }

    def listar(self, ruta: str) -> list[dict[str, Any]]:
        carpeta = self._buscar(ruta)
        if carpeta["tipo"] != "carpeta":
            raise ValueError("La ruta no corresponde a una carpeta.")
        self._exigir(carpeta, "lectura")
        return copy.deepcopy(carpeta["hijos"])

    def crear(self, ruta: str, nombre: str, tipo: str) -> dict[str, Any]:
        padre = self._buscar(ruta)
        if padre["tipo"] != "carpeta":
            raise ValueError("El destino debe ser una carpeta.")
        self._exigir(padre, "escritura")
        nombre = nombre.strip()
        if not nombre or nombre in (".", "..") or "/" in nombre or "\\" in nombre:
            raise ValueError("Escribe un nombre válido, sin separadores de ruta.")
        if tipo not in ("archivo", "carpeta"):
            raise ValueError("El tipo debe ser archivo o carpeta.")
        if any(hijo["nombre"] == nombre for hijo in padre["hijos"]):
            raise ValueError(f"Ya existe un elemento llamado «{nombre}» en esta carpeta.")
        ahora = self._ahora()
        nuevo = {
            "nombre": nombre,
            "tipo": tipo,
            "tamano": 0,
            "creado": ahora,
            "modificado": ahora,
            "permisos": {"lectura": True, "escritura": True, "ejecucion": tipo == "carpeta"},
            "contenido": "",
            "hijos": [],
        }
        padre["hijos"].append(nuevo)
        padre["modificado"] = ahora
        return copy.deepcopy(nuevo)

    def leer(self, ruta: str) -> str:
        elemento = self._buscar(ruta)
        if elemento["tipo"] != "archivo":
            raise ValueError("Solo se puede leer el contenido de un archivo.")
        self._exigir(elemento, "lectura")
        return elemento["contenido"]

    def modificar(self, ruta: str, contenido: str) -> None:
        elemento = self._buscar(ruta)
        if elemento["tipo"] != "archivo":
            raise ValueError("Solo se puede modificar un archivo.")
        self._exigir(elemento, "escritura")
        elemento["contenido"] = str(contenido)
        elemento["tamano"] = len(str(contenido).encode("utf-8"))
        elemento["modificado"] = self._ahora()

    def eliminar(self, ruta: str) -> None:
        ruta_normalizada = self._normalizar(ruta)
        if ruta_normalizada == "/":
            raise ValueError("No se puede eliminar la raíz del sistema.")
        padre_ruta, nombre = posixpath.split(ruta_normalizada)
        padre = self._buscar(padre_ruta or "/")
        self._exigir(padre, "escritura")
        for indice, hijo in enumerate(padre["hijos"]):
            if hijo["nombre"] == nombre:
                del padre["hijos"][indice]
                padre["modificado"] = self._ahora()
                return
        raise FileNotFoundError(f"No se encontró «{ruta_normalizada}».")

    def cambiar_permisos(self, ruta: str, permisos: dict[str, bool]) -> None:
        elemento = self._buscar(ruta)
        claves = ("lectura", "escritura", "ejecucion")
        if any(clave not in permisos for clave in claves):
            raise ValueError("Debes indicar lectura, escritura y ejecución.")
        elemento["permisos"] = {clave: bool(permisos[clave]) for clave in claves}
        elemento["modificado"] = self._ahora()

    def _buscar(self, ruta: str) -> dict[str, Any]:
        normalizada = self._normalizar(ruta)
        actual = self._raiz
        if normalizada == "/":
            return actual
        for parte in normalizada.strip("/").split("/"):
            if actual["tipo"] != "carpeta":
                raise NotADirectoryError(f"«{parte}» está dentro de un archivo.")
            siguiente = next((hijo for hijo in actual["hijos"] if hijo["nombre"] == parte), None)
            if siguiente is None:
                raise FileNotFoundError(f"No se encontró «{normalizada}».")
            actual = siguiente
        return actual

    @staticmethod
    def _normalizar(ruta: str) -> str:
        return posixpath.normpath("/" + str(ruta or "/").lstrip("/"))

    @staticmethod
    def _exigir(elemento: dict[str, Any], permiso: str) -> None:
        if not elemento.get("permisos", {}).get(permiso, False):
            raise PermissionError(f"El elemento no tiene permiso de {permiso}.")

    @staticmethod
    def _ahora() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M")


class Aplicacion:
    """Ventana principal; crea controladores y administra el único reloj."""

    def __init__(self, raiz: tk.Tk) -> None:
        self.raiz = raiz
        self.raiz.title("Simulador de administrador de tareas")
        self.raiz.geometry("680x390")
        self.raiz.minsize(560, 330)
        self.procesos = ControladorProcesosDemo()
        self.archivos = ControladorArchivosDemo()
        self.ventana_procesos: VentanaProcesos | None = None
        self.ventana_archivos: VentanaArchivos | None = None
        self.segundos = 0
        self._after_id: str | None = None

        marco = ttk.Frame(raiz, padding=24)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Simulador de sistema operativo", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(
            marco,
            text="Administra procesos y explora un sistema de archivos completamente virtual.",
            wraplength=580,
        ).pack(anchor="w", pady=(8, 22))

        botones = ttk.Frame(marco)
        botones.pack(fill="x")
        ttk.Button(botones, text="Administrador de procesos", command=self.abrir_procesos).pack(fill="x", pady=5, ipady=8)
        ttk.Button(botones, text="Sistema de archivos", command=self.abrir_archivos).pack(fill="x", pady=5, ipady=8)

        self.reloj = tk.StringVar(value="Tiempo simulado: 00:00")
        ttk.Label(marco, textvariable=self.reloj, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(22, 0))
        ttk.Label(
            marco,
            text="La demostración conserva sus cambios en memoria y no modifica procesos ni archivos reales.",
            wraplength=580,
        ).pack(anchor="w", pady=(8, 0))

        self.raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._programar_pulso()

    def abrir_procesos(self) -> None:
        if self.ventana_procesos is not None and self.ventana_procesos.existe():
            self.ventana_procesos.traer_al_frente()
            return
        self.ventana_procesos = VentanaProcesos(
            self.raiz, self.procesos, al_cerrar=lambda: setattr(self, "ventana_procesos", None)
        )

    def abrir_archivos(self) -> None:
        if self.ventana_archivos is not None and self.ventana_archivos.existe():
            self.ventana_archivos.traer_al_frente()
            return
        self.ventana_archivos = VentanaArchivos(
            self.raiz, self.archivos, al_cerrar=lambda: setattr(self, "ventana_archivos", None)
        )

    def _programar_pulso(self) -> None:
        self._after_id = self.raiz.after(1000, self._pulso)

    def _pulso(self) -> None:
        self.segundos += 1
        self.procesos.pulso()
        minutos, segundos = divmod(self.segundos, 60)
        self.reloj.set(f"Tiempo simulado: {minutos:02d}:{segundos:02d}")
        if self.ventana_procesos is not None and self.ventana_procesos.existe():
            self.ventana_procesos.actualizar()
        self._programar_pulso()

    def cerrar(self) -> None:
        if self._after_id is not None:
            try:
                self.raiz.after_cancel(self._after_id)
            except tk.TclError:
                pass
        self.raiz.destroy()


def main() -> None:
    raiz = tk.Tk()
    Aplicacion(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    try:
        main()
    except tk.TclError as error:
        messagebox.showerror("No se pudo iniciar la aplicación", str(error))
