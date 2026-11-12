"""Ventana del administrador de procesos (tabla de procesos y detalle del BCP).

La vista no decide reglas: pide cada acción al controlador y muestra lo que
devuelve. Si el controlador lanza un error, lo muestra en un messagebox.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable


def _formatear(clave: str, valor: Any) -> str:
    # Muestra los datos del BCP de forma legible en lugar de {'AX': 1, ...}.
    if clave == "tiempo_restante" and valor is None:
        return "∞ (proceso del sistema, no termina solo)"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, dict):
        return "  ".join(f"{nombre}={dato}" for nombre, dato in valor.items()) or "(vacío)"
    if isinstance(valor, list):
        return ", ".join(str(dato) for dato in valor) or "(ninguno)"
    return str(valor)


class VentanaProcesos:
    """Vista del administrador de procesos; las reglas viven en el controlador."""

    # Campos del BCP en el orden en que se muestran (nombres del README).
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
        ("critico", "Proceso crítico del sistema"),
    )

    # Color de fondo y de letra según el consumo que calcula el controlador.
    COLORES = {
        "Alto": ("#ffcdd2", "#b71c1c"),   # rojo: 1000 MB o más
        "Medio": ("#fff3c4", "#7a5a00"),  # amarillo: de 300 a 999 MB
        "Bajo": ("#c8e6c9", "#1b5e20"),   # verde: menos de 300 MB
        "—": ("#eeeeee", "#757575"),      # gris: proceso terminado
    }
    LEYENDA = (
        ("Alto", "Consumo alto (≥ 1000 MB)"),
        ("Medio", "Consumo medio (300–999 MB)"),
        ("Bajo", "Consumo bajo (< 300 MB)"),
        ("—", "Terminado"),
    )

    def __init__(
        self,
        master: tk.Misc,
        controlador: Any,
        al_cerrar: Callable[[], None] | None = None,
        al_fallo_critico: Callable[[dict[str, Any]], None] | None = None,
        al_buscar_archivo: Callable[[str], None] | None = None,
    ) -> None:
        self.controlador = controlador
        self.al_cerrar = al_cerrar
        # Función que da app.py para "apagar" el sistema si se detiene un
        # proceso crítico. Recibe el BCP del proceso detenido.
        self.al_fallo_critico = al_fallo_critico
        # Función que da app.py para mostrar un archivo en el Sistema de
        # archivos. Recibe la ruta del archivo.
        self.al_buscar_archivo = al_buscar_archivo
        self.ventana = tk.Toplevel(master)
        self.ventana.title("Administrador de procesos")
        self.ventana.geometry("1100x680")
        self.ventana.minsize(820, 500)
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

        columnas = ("pid", "ppid", "nombre", "usuario", "estado", "prioridad", "cpu", "restante", "memoria", "consumo")
        self.tabla = ttk.Treeview(contenedor, columns=columnas, show="headings", height=11, selectmode="browse")
        titulos = {
            "pid": "PID", "ppid": "PPID", "nombre": "Nombre", "usuario": "Usuario",
            "estado": "Estado", "prioridad": "Prioridad", "cpu": "CPU", "restante": "Restante",
            "memoria": "Memoria MB", "consumo": "Consumo",
        }
        anchos = {
            "pid": 50, "ppid": 50, "nombre": 170, "usuario": 90, "estado": 110, "prioridad": 70,
            "cpu": 60, "restante": 75, "memoria": 90, "consumo": 80,
        }
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="center" if columna not in ("nombre", "estado") else "w")
        self.tabla.pack(fill="both", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_detalle)
        # Menú de clic derecho (Button-3 en Linux/Windows, Button-2 en macOS).
        self.menu = tk.Menu(self.ventana, tearoff=False)
        self.tabla.bind("<Button-3>", self._menu_contextual)
        if self.ventana.tk.call("tk", "windowingsystem") == "aqua":
            self.tabla.bind("<Button-2>", self._menu_contextual)
        for consumo, (fondo, letra) in self.COLORES.items():
            self.tabla.tag_configure(consumo, background=fondo, foreground=letra)

        leyenda = ttk.Frame(contenedor)
        leyenda.pack(anchor="w", pady=(6, 0))
        for consumo, texto in self.LEYENDA:
            fondo, letra = self.COLORES[consumo]
            tk.Label(leyenda, text=f" {texto} ", background=fondo, foreground=letra,
                     relief="solid", borderwidth=1).pack(side="left", padx=(0, 6))
        ttk.Label(leyenda, text="  Ordenados de mayor a menor consumo. Los procesos de root son críticos.").pack(side="left")

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

    def _procesos(self) -> list[dict[str, Any]]:
        return list(self.controlador.listar() or [])

    def actualizar(self) -> None:
        seleccionado = self.tabla.selection()
        pid_anterior = seleccionado[0] if seleccionado else None
        try:
            procesos = self._procesos()
            # Como en el Administrador de tareas de Windows: arriba los que más
            # memoria consumen y los terminados al final.
            procesos.sort(key=lambda p: (p["estado"] == "Terminado", -p["memoria_mb"], p["pid"]))
            self.tabla.delete(*self.tabla.get_children())
            for proceso in procesos:
                restante = "∞" if proceso["tiempo_restante"] is None else proceso["tiempo_restante"]
                self.tabla.insert(
                    "", "end", iid=str(proceso["pid"]),
                    values=(
                        proceso["pid"], proceso["ppid"], proceso["nombre"],
                        proceso["usuario"], proceso["estado"],
                        proceso["prioridad"], proceso["tiempo_cpu"],
                        restante, proceso["memoria_mb"], proceso["consumo"],
                    ),
                    tags=(proceso["consumo"],),
                )
            if pid_anterior and self.tabla.exists(pid_anterior):
                self.tabla.selection_set(pid_anterior)
                self.tabla.focus(pid_anterior)
            elif self.tabla.get_children():
                self.tabla.selection_set(self.tabla.get_children()[0])
            self._mostrar_detalle()
            activos = sum(1 for p in procesos if p["estado"] != "Terminado")
            memoria = sum(p["memoria_mb"] for p in procesos if p["estado"] != "Terminado")
            self.estado.set(f"{activos} proceso(s) activo(s) usando {memoria} MB de memoria")
        except Exception as error:
            self.estado.set(f"No se pudo listar: {error}")

    def _mostrar_detalle(self, _evento: Any = None) -> None:
        seleccion = self.tabla.selection()
        pid = seleccion[0] if seleccion else ""
        proceso = next((p for p in self._procesos() if str(p["pid"]) == pid), None)
        contenido = "Sin proceso seleccionado." if proceso is None else "\n".join(
            f"{etiqueta}: {_formatear(clave, proceso.get(clave, '—'))}" for clave, etiqueta in self.CAMPOS
        )
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        self.detalle.insert("1.0", contenido)
        self.detalle.configure(state="disabled")

    # ------------------------------------------------------------------
    # Menú de clic derecho
    # ------------------------------------------------------------------

    def _menu_contextual(self, evento: Any) -> None:
        fila = self.tabla.identify_row(evento.y)
        if not fila:
            return
        self.tabla.selection_set(fila)
        self.tabla.focus(fila)
        proceso = next((p for p in self._procesos() if str(p["pid"]) == fila), None)
        if proceso is None:
            return
        archivos = list(proceso.get("archivos_abiertos") or [])
        ruta = archivos[0] if archivos else None
        estado_ruta = "normal" if ruta else "disabled"

        self.menu.delete(0, "end")
        self.menu.add_command(
            label="Abrir ubicación del archivo",
            state=estado_ruta if self.al_buscar_archivo else "disabled",
            command=lambda: self._buscar_archivo(ruta),
        )
        self.menu.add_command(label="Copiar ruta", state=estado_ruta, command=lambda: self._copiar_ruta(ruta))
        if not ruta:
            self.menu.add_separator()
            aviso = (
                "(El proceso terminó y ya liberó sus archivos)"
                if proceso["estado"] == "Terminado"
                else "(Este proceso no se abrió desde un archivo)"
            )
            self.menu.add_command(label=aviso, state="disabled")
        try:
            self.menu.tk_popup(evento.x_root, evento.y_root)
        finally:
            self.menu.grab_release()

    def _buscar_archivo(self, ruta: str | None) -> None:
        if not ruta or self.al_buscar_archivo is None:
            return
        try:
            self.al_buscar_archivo(ruta)
        except Exception as error:
            messagebox.showerror("No se pudo abrir la ubicación", str(error), parent=self.ventana)

    def _copiar_ruta(self, ruta: str | None) -> None:
        if not ruta:
            return
        self.ventana.clipboard_clear()
        self.ventana.clipboard_append(ruta)
        self.estado.set(f"Ruta copiada: {ruta}")

    def crear(self) -> None:
        nombre = simpledialog.askstring("Crear proceso", "Nombre del proceso:", parent=self.ventana)
        if nombre is None:
            return
        prioridad = simpledialog.askinteger(
            "Crear proceso", "Prioridad (0 = más importante, 10 = menos importante):",
            parent=self.ventana, minvalue=0, maxvalue=10,
        )
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

    def _confirmar_critico(self, proceso: dict[str, Any], nombre_accion: str) -> bool:
        # Aviso antes de pausar o detener un proceso del sistema.
        consecuencia = (
            "Si lo detienes, el sistema se apagará."
            if nombre_accion == "detener"
            else "Si lo pausas, el sistema puede dejar de responder."
        )
        return messagebox.askyesno(
            "⚠ Proceso crítico del sistema",
            f"«{proceso['nombre']}» (PID {proceso['pid']}) es un proceso crítico del sistema.\n\n"
            f"{consecuencia}\n\n¿Sabes lo que haces? ¿Quieres {nombre_accion}lo?",
            icon="warning", default="no", parent=self.ventana,
        )

    def _ofrecer_relanzar(self, proceso: dict[str, Any]) -> None:
        # Un proceso terminado no revive; se ofrece abrir uno nuevo.
        if proceso.get("critico"):
            messagebox.showinfo(
                "Proceso del sistema",
                "Los procesos del sistema solo arrancan al encender el equipo.",
                parent=self.ventana,
            )
            return
        if not messagebox.askyesno(
            "El proceso ya terminó",
            f"«{proceso['nombre']}» (PID {proceso['pid']}) ya terminó y liberó sus recursos, "
            "así que no puede volver a ejecutarse.\n\n"
            "¿Quieres abrirlo de nuevo como un proceso nuevo (con otro PID)?",
            parent=self.ventana,
        ):
            return
        try:
            nuevo = self.controlador.relanzar(proceso["pid"])
        except Exception as error:
            messagebox.showerror("No se pudo abrir de nuevo", str(error), parent=self.ventana)
            return
        self.actualizar()
        self.tabla.selection_set(str(nuevo["pid"]))
        self.tabla.see(str(nuevo["pid"]))
        self.estado.set(f"{nuevo['nombre']} se abrió de nuevo como PID {nuevo['pid']}")

    def accion(self, nombre_accion: str) -> None:
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Selecciona un proceso", "Elige un proceso de la lista primero.", parent=self.ventana)
            return
        pid = int(seleccion[0])
        proceso = next((p for p in self._procesos() if p["pid"] == pid), None)
        if (
            proceso is not None
            and proceso.get("critico")
            and nombre_accion in ("pausar", "detener")
            and not self._confirmar_critico(proceso, nombre_accion)
        ):
            self.estado.set("Acción cancelada")
            return
        if proceso is not None and proceso["estado"] == "Terminado" and nombre_accion == "ejecutar":
            self._ofrecer_relanzar(proceso)
            return
        try:
            resultado = getattr(self.controlador, nombre_accion)(pid)
        except Exception as error:
            messagebox.showerror("No se pudo realizar la acción", str(error), parent=self.ventana)
            return
        self.actualizar()
        # El controlador devuelve el BCP actualizado; la vista solo arma el mensaje.
        self.estado.set(f"{resultado['nombre']} (PID {resultado['pid']}): {resultado['estado']}")
        if nombre_accion == "detener" and resultado.get("critico") and self.al_fallo_critico:
            self.al_fallo_critico(resultado)
