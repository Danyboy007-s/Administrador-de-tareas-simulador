"""Ventanas Tkinter para el simulador de procesos y sistema de archivos."""

from __future__ import annotations

import posixpath
import tkinter as tk
from collections.abc import Mapping
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable


# Datos de ejemplo mientras se conectan los controladores definitivos.
PROCESOS_EJEMPLO = [
    {
        "pid": 101,
        "ppid": 1,
        "nombre": "Explorador",
        "usuario": "usuario",
        "estado": "Listo",
        "contador_programa": 0,
        "registros": {"AX": "0000", "BX": "0000", "CX": "0000", "DX": "0000"},
        "prioridad": 5,
        "tiempo_cpu": 0,
        "tiempo_restante": 8,
        "memoria_mb": 48,
        "archivos_abiertos": ["/documentos"],
        "dispositivos": [],
    },
    {
        "pid": 102,
        "ppid": 1,
        "nombre": "Editor de texto",
        "usuario": "usuario",
        "estado": "En espera",
        "contador_programa": 2,
        "registros": {"AX": "0001", "BX": "0000", "CX": "0002", "DX": "0000"},
        "prioridad": 3,
        "tiempo_cpu": 2,
        "tiempo_restante": 12,
        "memoria_mb": 96,
        "archivos_abiertos": ["/documentos/notas.txt"],
        "dispositivos": ["teclado"],
    },
]

SISTEMA_ARCHIVOS_EJEMPLO = [
    {
        "nombre": "documentos",
        "tipo": "carpeta",
        "tamano": 0,
        "creado": "2026-11-11 09:00",
        "modificado": "2026-11-11 09:00",
        "permisos": {"lectura": True, "escritura": True, "ejecucion": True},
        "contenido": "",
        "hijos": [
            {
                "nombre": "notas.txt",
                "tipo": "archivo",
                "tamano": 42,
                "creado": "2026-11-11 09:10",
                "modificado": "2026-11-11 09:10",
                "permisos": {"lectura": True, "escritura": True, "ejecucion": False},
                "contenido": "Notas de ejemplo del sistema simulado.",
                "hijos": [],
            },
            {
                "nombre": "proyectos",
                "tipo": "carpeta",
                "tamano": 0,
                "creado": "2026-11-11 09:15",
                "modificado": "2026-11-11 09:15",
                "permisos": {"lectura": True, "escritura": True, "ejecucion": True},
                "contenido": "",
                "hijos": [],
            },
        ],
    },
    {
        "nombre": "bienvenida.txt",
        "tipo": "archivo",
        "tamano": 34,
        "creado": "2026-11-11 09:00",
        "modificado": "2026-11-11 09:00",
        "permisos": {"lectura": True, "escritura": True, "ejecucion": False},
        "contenido": "Bienvenido al sistema de archivos simulado.",
        "hijos": [],
    },
]


def _campo(elemento: Any, nombre: str, predeterminado: Any = "") -> Any:
    """Lee un campo tanto de modelos tipo objeto como de diccionarios."""
    if isinstance(elemento, Mapping):
        return elemento.get(nombre, predeterminado)
    return getattr(elemento, nombre, predeterminado)


def _texto_permisos(permisos: Any) -> str:
    if isinstance(permisos, Mapping):
        return " ".join(
            f"{clave[0].upper()}:{'sí' if permisos.get(clave, False) else 'no'}"
            for clave in ("lectura", "escritura", "ejecucion")
        )
    return str(permisos or "")


class VentanaProcesos:
    """Vista del administrador de procesos; las reglas viven en el controlador."""

    CAMPOS = (
        ("pid", "PID"),
        ("ppid", "PPID"),
        ("nombre", "Nombre"),
        ("usuario", "Usuario"),
        ("estado", "Estado"),
        ("contador_programa", "Contador de programa"),
        ("registros", "Registros"),
        ("prioridad", "Prioridad"),
        ("tiempo_cpu", "Tiempo de CPU"),
        ("tiempo_restante", "Tiempo restante"),
        ("memoria_mb", "Memoria (MB)"),
        ("archivos_abiertos", "Archivos abiertos"),
        ("dispositivos", "Dispositivos"),
    )

    def __init__(
        self,
        master: tk.Misc,
        controlador: Any,
        al_cerrar: Callable[[], None] | None = None,
    ) -> None:
        self.controlador = controlador
        self.al_cerrar = al_cerrar
        self.ventana = tk.Toplevel(master)
        self.ventana.title("Administrador de procesos")
        self.ventana.geometry("1050x650")
        self.ventana.minsize(800, 480)
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)

        contenedor = ttk.Frame(self.ventana, padding=12)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(
            contenedor,
            text="Administrador de procesos",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        barra = ttk.Frame(contenedor)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Crear proceso", command=self.crear).pack(side="left", padx=(0, 6))
        ttk.Button(barra, text="Ejecutar", command=lambda: self.accion("ejecutar")).pack(side="left", padx=3)
        ttk.Button(barra, text="Pausar", command=lambda: self.accion("pausar")).pack(side="left", padx=3)
        ttk.Button(barra, text="Detener", command=lambda: self.accion("detener")).pack(side="left", padx=3)
        ttk.Button(barra, text="Actualizar", command=self.actualizar).pack(side="right")

        columnas = ("pid", "ppid", "nombre", "usuario", "estado", "prioridad", "cpu", "restante", "memoria")
        self.tabla = ttk.Treeview(contenedor, columns=columnas, show="headings", height=11, selectmode="browse")
        titulos = {
            "pid": "PID", "ppid": "PPID", "nombre": "Nombre", "usuario": "Usuario",
            "estado": "Estado", "prioridad": "Prioridad", "cpu": "CPU", "restante": "Restante", "memoria": "Memoria MB",
        }
        anchos = {"pid": 55, "ppid": 55, "nombre": 170, "usuario": 100, "estado": 120, "prioridad": 75, "cpu": 65, "restante": 80, "memoria": 90}
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="center" if columna not in ("nombre", "estado") else "w")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_detalle)

        ttk.Label(contenedor, text="Bloque de Control de Proceso (BCP)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(12, 4))
        self.detalle = tk.Text(contenedor, height=8, wrap="word", state="disabled", relief="solid", borderwidth=1)
        self.detalle.pack(fill="x")
        self.estado = tk.StringVar(value="Listo")
        ttk.Label(contenedor, textvariable=self.estado).pack(anchor="w", pady=(8, 0))
        self.actualizar()

    def existe(self) -> bool:
        return bool(self.ventana.winfo_exists())

    def traer_al_frente(self) -> None:
        if self.existe():
            self.ventana.deiconify()
            self.ventana.lift()
            self.ventana.focus_set()

    def cerrar(self) -> None:
        if self.al_cerrar:
            self.al_cerrar()
        self.ventana.destroy()

    def _procesos(self) -> list[Any]:
        return list(self.controlador.listar() or [])

    def actualizar(self) -> None:
        seleccionado = self.tabla.selection()
        pid_anterior = seleccionado[0] if seleccionado else None
        try:
            procesos = self._procesos()
            self.tabla.delete(*self.tabla.get_children())
            for proceso in procesos:
                pid = _campo(proceso, "pid")
                if pid is None:
                    continue
                self.tabla.insert(
                    "", "end", iid=str(pid),
                    values=(
                        pid, _campo(proceso, "ppid"), _campo(proceso, "nombre"),
                        _campo(proceso, "usuario"), _campo(proceso, "estado"),
                        _campo(proceso, "prioridad"), _campo(proceso, "tiempo_cpu"),
                        _campo(proceso, "tiempo_restante"), _campo(proceso, "memoria_mb"),
                    ),
                )
            if pid_anterior and self.tabla.exists(pid_anterior):
                self.tabla.selection_set(pid_anterior)
                self.tabla.focus(pid_anterior)
            elif self.tabla.get_children():
                primero = self.tabla.get_children()[0]
                self.tabla.selection_set(primero)
            self._mostrar_detalle()
            self.estado.set(f"{len(procesos)} proceso(s)")
        except Exception as error:
            self.estado.set(f"No se pudo listar: {error}")

    def _mostrar_detalle(self, _evento: Any = None) -> None:
        seleccion = self.tabla.selection()
        proceso = next(
            (item for item in self._procesos() if str(_campo(item, "pid")) == (seleccion[0] if seleccion else "")),
            None,
        )
        contenido = "Sin proceso seleccionado." if proceso is None else "\n".join(
            f"{etiqueta}: {_campo(proceso, clave, '—')}" for clave, etiqueta in self.CAMPOS
        )
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", contenido)
        self.detalle.configure(state="disabled")

    def crear(self) -> None:
        nombre = simpledialog.askstring("Crear proceso", "Nombre del proceso:", parent=self.ventana)
        if nombre is None:
            return
        prioridad = simpledialog.askinteger("Crear proceso", "Prioridad (1 a 10):", parent=self.ventana, minvalue=1, maxvalue=10)
        if prioridad is None:
            return
        memoria = simpledialog.askinteger("Crear proceso", "Memoria requerida (MB):", parent=self.ventana, minvalue=1)
        if memoria is None:
            return
        try:
            self.controlador.crear(nombre.strip(), prioridad, memoria)
            self.actualizar()
            self.estado.set(f"Proceso «{nombre.strip()}» creado")
        except Exception as error:
            messagebox.showerror("No se pudo crear el proceso", str(error), parent=self.ventana)

    def accion(self, nombre_accion: str) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Selecciona un proceso", "Elige un proceso de la lista primero.", parent=self.ventana)
            return
        try:
            resultado = getattr(self.controlador, nombre_accion)(int(seleccion[0]))
            self.actualizar()
            self.estado.set(str(resultado) if resultado not in (None, True) else f"Acción «{nombre_accion}» completada")
        except Exception as error:
            messagebox.showerror("No se pudo realizar la acción", str(error), parent=self.ventana)


class VentanaArchivos:
    """Vista del sistema de archivos virtual; no accede al disco del equipo."""

    def __init__(
        self,
        master: tk.Misc,
        controlador: Any,
        al_cerrar: Callable[[], None] | None = None,
    ) -> None:
        self.controlador = controlador
        self.al_cerrar = al_cerrar
        self.ruta = "/"
        self.ventana = tk.Toplevel(master)
        self.ventana.title("Sistema de archivos simulado")
        self.ventana.geometry("1000x600")
        self.ventana.minsize(760, 440)
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)

        contenedor = ttk.Frame(self.ventana, padding=12)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(contenedor, text="Sistema de archivos simulado", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 10))

        barra = ttk.Frame(contenedor)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Atrás", command=self.atras).pack(side="left", padx=(0, 6))
        self.ruta_texto = tk.StringVar(value=self.ruta)
        ttk.Label(barra, text="Ubicación:").pack(side="left")
        ttk.Label(barra, textvariable=self.ruta_texto, font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        ttk.Button(barra, text="Crear archivo", command=lambda: self.crear("archivo")).pack(side="right", padx=(6, 0))
        ttk.Button(barra, text="Crear carpeta", command=lambda: self.crear("carpeta")).pack(side="right", padx=6)

        acciones = ttk.Frame(contenedor)
        acciones.pack(fill="x", pady=(0, 8))
        ttk.Button(acciones, text="Abrir / leer", command=self.leer).pack(side="left", padx=(0, 6))
        ttk.Button(acciones, text="Modificar", command=self.modificar).pack(side="left", padx=3)
        ttk.Button(acciones, text="Eliminar", command=self.eliminar).pack(side="left", padx=3)
        ttk.Button(acciones, text="Permisos", command=self.permisos).pack(side="left", padx=3)
        ttk.Button(acciones, text="Actualizar", command=self.actualizar).pack(side="right")

        columnas = ("nombre", "tipo", "tamano", "creado", "modificado", "permisos")
        self.tabla = ttk.Treeview(contenedor, columns=columnas, show="headings", selectmode="browse")
        titulos = {"nombre": "Nombre", "tipo": "Tipo", "tamano": "Tamaño", "creado": "Creado", "modificado": "Modificado", "permisos": "Permisos"}
        anchos = {"nombre": 250, "tipo": 100, "tamano": 90, "creado": 140, "modificado": 140, "permisos": 220}
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="w")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<Double-1>", self.abrir_seleccion)
        self.estado = tk.StringVar(value="Doble clic en una carpeta para entrar.")
        ttk.Label(contenedor, textvariable=self.estado).pack(anchor="w", pady=(8, 0))
        self.actualizar()

    def existe(self) -> bool:
        return bool(self.ventana.winfo_exists())

    def traer_al_frente(self) -> None:
        if self.existe():
            self.ventana.deiconify()
            self.ventana.lift()
            self.ventana.focus_set()

    def cerrar(self) -> None:
        if self.al_cerrar:
            self.al_cerrar()
        self.ventana.destroy()

    def _ruta_elemento(self, elemento: Any) -> str:
        nombre = str(_campo(elemento, "nombre", ""))
        return posixpath.normpath(posixpath.join(self.ruta, nombre))

    def _seleccion(self) -> tuple[str, Any] | None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Selecciona un elemento", "Elige un archivo o carpeta de la lista.", parent=self.ventana)
            return None
        ruta = seleccion[0]
        elemento = next((item for item in self.controlador.listar(self.ruta) or [] if self._ruta_elemento(item) == ruta), None)
        return (ruta, elemento) if elemento is not None else (ruta, None)

    def actualizar(self) -> None:
        self.ruta_texto.set(self.ruta)
        try:
            elementos = list(self.controlador.listar(self.ruta) or [])
            self.tabla.delete(*self.tabla.get_children())
            for elemento in elementos:
                nombre = str(_campo(elemento, "nombre", ""))
                if not nombre:
                    continue
                ruta = self._ruta_elemento(elemento)
                self.tabla.insert(
                    "", "end", iid=ruta,
                    values=(
                        nombre, _campo(elemento, "tipo"), _campo(elemento, "tamano", 0),
                        _campo(elemento, "creado"), _campo(elemento, "modificado"),
                        _texto_permisos(_campo(elemento, "permisos", {})),
                    ),
                )
            self.estado.set(f"{len(elementos)} elemento(s). Doble clic en una carpeta para entrar.")
        except Exception as error:
            self.estado.set(f"No se pudo listar la carpeta: {error}")

    def atras(self) -> None:
        if self.ruta != "/":
            self.ruta = posixpath.dirname(self.ruta.rstrip("/")) or "/"
            self.actualizar()

    def abrir_seleccion(self, _evento: Any = None) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        if elemento is not None and _campo(elemento, "tipo") == "carpeta":
            self.ruta = ruta
            self.actualizar()
        else:
            self.leer()

    def crear(self, tipo: str) -> None:
        nombre = simpledialog.askstring("Crear elemento", f"Nombre del {tipo}:", parent=self.ventana)
        if nombre is None:
            return
        try:
            self.controlador.crear(self.ruta, nombre.strip(), tipo)
            self.actualizar()
            self.estado.set(f"{tipo.capitalize()} «{nombre.strip()}» creado")
        except Exception as error:
            messagebox.showerror("No se pudo crear", str(error), parent=self.ventana)

    def leer(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        if elemento is not None and _campo(elemento, "tipo") == "carpeta":
            self.ruta = ruta
            self.actualizar()
            return
        try:
            contenido = self.controlador.leer(ruta)
            ventana = tk.Toplevel(self.ventana)
            ventana.title(f"Lectura: {posixpath.basename(ruta)}")
            ventana.geometry("560x380")
            texto = tk.Text(ventana, wrap="word")
            texto.pack(fill="both", expand=True, padx=10, pady=10)
            texto.insert("1.0", str(contenido))
            texto.configure(state="disabled")
        except Exception as error:
            messagebox.showerror("No se pudo leer", str(error), parent=self.ventana)

    def modificar(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        if elemento is not None and _campo(elemento, "tipo") == "carpeta":
            messagebox.showinfo("Modificar archivo", "Selecciona un archivo, no una carpeta.", parent=self.ventana)
            return
        try:
            contenido = self.controlador.leer(ruta)
        except Exception as error:
            messagebox.showerror("No se pudo abrir el archivo", str(error), parent=self.ventana)
            return

        editor = tk.Toplevel(self.ventana)
        editor.title(f"Modificar: {posixpath.basename(ruta)}")
        editor.geometry("620x440")
        caja = tk.Text(editor, wrap="word")
        caja.pack(fill="both", expand=True, padx=10, pady=10)
        caja.insert("1.0", str(contenido))

        def guardar() -> None:
            try:
                self.controlador.modificar(ruta, caja.get("1.0", "end-1c"))
                self.actualizar()
                self.estado.set(f"Archivo «{posixpath.basename(ruta)}» modificado")
                editor.destroy()
            except Exception as error:
                messagebox.showerror("No se pudo modificar", str(error), parent=editor)

        ttk.Button(editor, text="Guardar cambios", command=guardar).pack(anchor="e", padx=10, pady=(0, 10))

    def eliminar(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, _elemento = seleccionado
        if not messagebox.askyesno("Eliminar elemento", f"¿Eliminar «{posixpath.basename(ruta)}» del sistema simulado?", parent=self.ventana):
            return
        try:
            self.controlador.eliminar(ruta)
            self.actualizar()
        except Exception as error:
            messagebox.showerror("No se pudo eliminar", str(error), parent=self.ventana)

    def permisos(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        permisos_actuales = _campo(elemento, "permisos", {}) if elemento is not None else {}
        dialogo = tk.Toplevel(self.ventana)
        dialogo.title(f"Permisos: {posixpath.basename(ruta)}")
        dialogo.transient(self.ventana)
        dialogo.grab_set()
        marco = ttk.Frame(dialogo, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Permisos del elemento").pack(anchor="w", pady=(0, 8))
        variables: dict[str, tk.BooleanVar] = {}
        for clave, etiqueta in (("lectura", "Lectura"), ("escritura", "Escritura"), ("ejecucion", "Ejecución")):
            valor = permisos_actuales.get(clave, False) if isinstance(permisos_actuales, Mapping) else False
            variables[clave] = tk.BooleanVar(value=bool(valor))
            ttk.Checkbutton(marco, text=etiqueta, variable=variables[clave]).pack(anchor="w", pady=2)

        def guardar() -> None:
            try:
                self.controlador.cambiar_permisos(ruta, {clave: variable.get() for clave, variable in variables.items()})
                self.actualizar()
                dialogo.destroy()
            except Exception as error:
                messagebox.showerror("No se pudieron cambiar los permisos", str(error), parent=dialogo)

        ttk.Button(marco, text="Guardar", command=guardar).pack(anchor="e", pady=(10, 0))
