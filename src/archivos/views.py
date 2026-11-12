"""Ventana del sistema de archivos simulado (árbol de carpetas, íconos y contenido).

A la izquierda está el árbol jerárquico de carpetas y a la derecha el contenido
de la carpeta actual. La vista no decide reglas: pide cada acción al
controlador y, si falta un permiso, muestra el error que este lanza.
"""

from __future__ import annotations

import posixpath
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Callable


# ----------------------------------------------------------------------
# Íconos de 16x16 dibujados con rectángulos. Se dibujan en lugar de usar
# imágenes o emojis para no depender de archivos externos ni de fuentes.
# ----------------------------------------------------------------------

def _dibujar(rectangulos: list[tuple[str, tuple[int, int, int, int]]]) -> tk.PhotoImage:
    imagen = tk.PhotoImage(width=16, height=16)
    for color, area in rectangulos:
        imagen.put(color, to=area)
    return imagen


def _crear_iconos() -> dict[str, tk.PhotoImage]:
    def carpeta(borde: str, relleno: str) -> tk.PhotoImage:
        return _dibujar([
            (borde, (1, 2, 7, 4)),     # pestaña
            (borde, (0, 4, 16, 14)),   # contorno
            (relleno, (1, 5, 15, 13)), # cuerpo
        ])

    def archivo(relleno: str, lineas: str) -> tk.PhotoImage:
        return _dibujar([
            ("#7a7a7a", (3, 1, 13, 15)),  # contorno de la hoja
            (relleno, (4, 2, 12, 14)),    # hoja
            (lineas, (5, 5, 11, 6)),      # renglones de texto
            (lineas, (5, 8, 11, 9)),
            (lineas, (5, 11, 9, 12)),
        ])

    return {
        "carpeta": carpeta("#c9932b", "#f2c14e"),
        "carpeta_bloqueada": carpeta("#7a7a7a", "#c4c4c4"),  # sin permiso para entrar
        "archivo": archivo("#ffffff", "#9aa5b1"),
        "ejecutable": archivo("#e3f4e4", "#2e7d32"),         # tiene permiso de ejecución
    }


def _texto_permisos(elemento: dict[str, Any]) -> str:
    # Formato tipo Linux: d = carpeta, - = archivo, luego r w x o "-".
    permisos = elemento.get("permisos", {})
    letras = "".join(
        letra if permisos.get(clave) else "-"
        for clave, letra in (("lectura", "r"), ("escritura", "w"), ("ejecucion", "x"))
    )
    return ("d" if elemento.get("tipo") == "carpeta" else "-") + letras


def _texto_tamano(elemento: dict[str, Any]) -> str:
    # Muestra el tamaño en la unidad más cómoda: B, KB, MB o GB.
    if elemento.get("tipo") == "carpeta":
        return "—"
    tamano = float(elemento.get("tamano", 0))
    for unidad in ("B", "KB", "MB"):
        if tamano < 1024:
            return f"{tamano:.0f} {unidad}" if unidad == "B" else f"{tamano:.1f} {unidad}"
        tamano /= 1024
    return f"{tamano:.1f} GB"


class VentanaArchivos:
    """Vista del sistema de archivos virtual; no accede al disco del equipo."""

    def __init__(
        self,
        master: tk.Misc,
        controlador: Any,
        al_cerrar: Callable[[], None] | None = None,
        al_ejecutar: Callable[[str], str] | None = None,
    ) -> None:
        self.controlador = controlador
        self.al_cerrar = al_cerrar
        # Función que da app.py para ejecutar un archivo como proceso.
        # Recibe la ruta y devuelve un mensaje para mostrar.
        self.al_ejecutar = al_ejecutar
        self.ruta = "/"
        # Elementos de la carpeta actual por ruta, para no volver a pedirlos.
        self.elementos: dict[str, dict[str, Any]] = {}

        self.ventana = tk.Toplevel(master)
        self.ventana.title("Sistema de archivos simulado")
        self.ventana.geometry("1100x620")
        self.ventana.minsize(820, 460)
        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)
        # Hay que guardar los íconos en self; si no, Python los borra y no se ven.
        self.iconos = _crear_iconos()

        contenedor = ttk.Frame(self.ventana, padding=12)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(contenedor, text="Sistema de archivos simulado", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 10))

        # Barra de ubicación
        barra = ttk.Frame(contenedor)
        barra.pack(fill="x", pady=(0, 8))
        ttk.Button(barra, text="Subir", command=self.subir).pack(side="left", padx=(0, 6))
        ttk.Label(barra, text="Ubicación:").pack(side="left")
        self.ruta_texto = tk.StringVar(value=self.ruta)
        ttk.Label(barra, textvariable=self.ruta_texto, font=("Segoe UI", 10, "bold")).pack(side="left", padx=5)
        ttk.Button(barra, text="Instalar programa", command=self.instalar).pack(side="right", padx=(6, 0))
        ttk.Button(barra, text="Crear archivo", command=lambda: self.crear("archivo")).pack(side="right", padx=(6, 0))
        ttk.Button(barra, text="Crear carpeta", command=lambda: self.crear("carpeta")).pack(side="right", padx=6)

        # Barra de acciones
        acciones = ttk.Frame(contenedor)
        acciones.pack(fill="x", pady=(0, 8))
        ttk.Button(acciones, text="Abrir / leer", command=self.leer).pack(side="left", padx=(0, 6))
        ttk.Button(acciones, text="Modificar", command=self.modificar).pack(side="left", padx=3)
        ttk.Button(acciones, text="Eliminar", command=self.eliminar).pack(side="left", padx=3)
        ttk.Button(acciones, text="Permisos", command=self.permisos).pack(side="left", padx=3)
        if self.al_ejecutar is not None:
            ttk.Button(acciones, text="Ejecutar", command=self.ejecutar).pack(side="left", padx=3)
        ttk.Button(acciones, text="Actualizar", command=self.actualizar).pack(side="right")

        # Panel dividido: árbol a la izquierda, contenido a la derecha
        panel = ttk.PanedWindow(contenedor, orient="horizontal")
        panel.pack(fill="both", expand=True)

        marco_arbol = ttk.Frame(panel)
        self.arbol = ttk.Treeview(marco_arbol, show="tree", selectmode="browse")
        self.arbol.column("#0", width=230)
        barra_arbol = ttk.Scrollbar(marco_arbol, orient="vertical", command=self.arbol.yview)
        self.arbol.configure(yscrollcommand=barra_arbol.set)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra_arbol.pack(side="right", fill="y")
        self.arbol.bind("<<TreeviewSelect>>", self._al_elegir_en_arbol)
        panel.add(marco_arbol, weight=1)

        marco_tabla = ttk.Frame(panel)
        columnas = ("tipo", "tamano", "creado", "modificado", "permisos")
        self.tabla = ttk.Treeview(marco_tabla, columns=columnas, show="tree headings", selectmode="browse")
        self.tabla.heading("#0", text="Nombre")
        self.tabla.column("#0", width=230)
        titulos = {"tipo": "Tipo", "tamano": "Tamaño", "creado": "Creado", "modificado": "Modificado", "permisos": "Permisos"}
        anchos = {"tipo": 80, "tamano": 80, "creado": 130, "modificado": 130, "permisos": 80}
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="w")
        barra_tabla = ttk.Scrollbar(marco_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_tabla.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra_tabla.pack(side="right", fill="y")
        self.tabla.bind("<Double-1>", self.abrir_seleccion)
        self.tabla.bind("<<TreeviewSelect>>", self._mostrar_propiedades)
        panel.add(marco_tabla, weight=3)

        # Propiedades del elemento seleccionado
        self.propiedades = tk.StringVar(value="")
        ttk.Label(contenedor, textvariable=self.propiedades).pack(anchor="w", pady=(8, 0))
        self.estado = tk.StringVar(value="Doble clic en una carpeta para entrar.")
        ttk.Label(contenedor, textvariable=self.estado).pack(anchor="w", pady=(2, 0))
        self.actualizar()

    # ------------------------------------------------------------------
    # Ventana
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Dibujar el árbol y la tabla
    # ------------------------------------------------------------------

    def _icono(self, elemento: dict[str, Any]) -> tk.PhotoImage:
        permisos = elemento.get("permisos", {})
        if elemento.get("tipo") == "carpeta":
            return self.iconos["carpeta" if permisos.get("ejecucion") else "carpeta_bloqueada"]
        return self.iconos["ejecutable" if permisos.get("ejecucion") else "archivo"]

    def _llenar_arbol(self, nodo: str) -> None:
        # Pide al controlador las subcarpetas de "nodo" y las agrega al árbol.
        # Se llama a sí misma con cada subcarpeta (recursión) hasta recorrer
        # todo el sistema. Si una carpeta no se puede abrir, queda sin hijos.
        try:
            hijos = self.controlador.listar(nodo)
        except Exception:
            return
        for hijo in hijos:
            if hijo.get("tipo") != "carpeta":
                continue
            ruta = posixpath.join(nodo, hijo["nombre"])
            self.arbol.insert(nodo, "end", iid=ruta, text=" " + hijo["nombre"], image=self._icono(hijo))
            self._llenar_arbol(ruta)

    def _dibujar_arbol(self) -> None:
        # Recuerda qué carpetas estaban abiertas para dejarlas igual.
        abiertas = {"/"} | {nodo for nodo in self._todos_los_nodos() if self.arbol.item(nodo, "open")}
        self.arbol.delete(*self.arbol.get_children())
        self.arbol.insert("", "end", iid="/", text=" / (raíz)", image=self.iconos["carpeta"])
        self._llenar_arbol("/")
        # La ruta actual y sus carpetas padre siempre quedan abiertas.
        ruta = self.ruta
        while ruta != "/":
            abiertas.add(ruta)
            ruta = posixpath.dirname(ruta)
        for nodo in abiertas:
            if self.arbol.exists(nodo):
                self.arbol.item(nodo, open=True)
        if self.arbol.exists(self.ruta):
            self.arbol.selection_set(self.ruta)
            self.arbol.see(self.ruta)

    def _todos_los_nodos(self, padre: str = "") -> list[str]:
        nodos = []
        for nodo in self.arbol.get_children(padre):
            nodos.append(nodo)
            nodos.extend(self._todos_los_nodos(nodo))
        return nodos

    def _dibujar_tabla(self, elementos: list[dict[str, Any]]) -> None:
        self.tabla.delete(*self.tabla.get_children())
        self.elementos = {}
        for elemento in elementos:
            ruta = posixpath.join(self.ruta, elemento["nombre"])
            self.elementos[ruta] = elemento
            self.tabla.insert(
                "", "end", iid=ruta,
                text=" " + elemento["nombre"],
                image=self._icono(elemento),
                values=(
                    elemento["tipo"], _texto_tamano(elemento),
                    elemento["creado"], elemento["modificado"],
                    _texto_permisos(elemento),
                ),
            )
        self.propiedades.set("")

    def actualizar(self) -> None:
        # Si la carpeta actual ya no se puede abrir (por ejemplo, le quitaron
        # un permiso), se sube hasta la primera carpeta que sí se pueda.
        while True:
            try:
                elementos = list(self.controlador.listar(self.ruta) or [])
                break
            except Exception as error:
                if self.ruta == "/":
                    self.estado.set(f"No se pudo listar la raíz: {error}")
                    return
                self.ruta = posixpath.dirname(self.ruta)
        self.ruta_texto.set(self.ruta)
        self._dibujar_tabla(elementos)
        self._dibujar_arbol()
        self.estado.set(f"{len(elementos)} elemento(s). Doble clic en una carpeta para entrar.")

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------

    def ir_a(self, ruta: str) -> None:
        # Primero pregunta al controlador; solo cambia de carpeta si se puede.
        try:
            elementos = list(self.controlador.listar(ruta) or [])
        except Exception as error:
            messagebox.showerror("No se pudo abrir la carpeta", str(error), parent=self.ventana)
            if self.arbol.exists(self.ruta):
                self.arbol.selection_set(self.ruta)
            return
        self.ruta = ruta
        self.ruta_texto.set(ruta)
        self._dibujar_tabla(elementos)
        if self.arbol.exists(ruta):
            self.arbol.selection_set(ruta)
            self.arbol.see(ruta)
        self.estado.set(f"{len(elementos)} elemento(s). Doble clic en una carpeta para entrar.")

    def _al_elegir_en_arbol(self, _evento: Any = None) -> None:
        seleccion = self.arbol.selection()
        if seleccion and seleccion[0] != self.ruta:
            self.ir_a(seleccion[0])

    def subir(self) -> None:
        if self.ruta != "/":
            self.ir_a(posixpath.dirname(self.ruta))

    def _seleccion(self) -> tuple[str, dict[str, Any]] | None:
        seleccion = self.tabla.selection()
        if not seleccion or seleccion[0] not in self.elementos:
            messagebox.showinfo("Selecciona un elemento", "Elige un archivo o carpeta de la lista.", parent=self.ventana)
            return None
        return seleccion[0], self.elementos[seleccion[0]]

    def _mostrar_propiedades(self, _evento: Any = None) -> None:
        seleccion = self.tabla.selection()
        if not seleccion or seleccion[0] not in self.elementos:
            self.propiedades.set("")
            return
        elemento = self.elementos[seleccion[0]]
        self.propiedades.set(
            f"Ruta: {seleccion[0]}   |   Tipo: {elemento['tipo']}   |   "
            f"Tamaño: {_texto_tamano(elemento)}   |   Permisos: {_texto_permisos(elemento)}"
        )

    def abrir_seleccion(self, _evento: Any = None) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        if elemento["tipo"] == "carpeta":
            self.ir_a(ruta)
        else:
            self.leer()

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------

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

    def instalar(self) -> None:
        # Simula instalar un programa: solo se indica nombre y tamaño.
        nombre = simpledialog.askstring("Instalar programa", "Nombre del programa:", parent=self.ventana)
        if nombre is None:
            return
        tamano = simpledialog.askinteger(
            "Instalar programa",
            "Tamaño del programa en MB:\n(más tamaño = más memoria al ejecutarlo)",
            parent=self.ventana, minvalue=1, maxvalue=100000,
        )
        if tamano is None:
            return
        try:
            programa = self.controlador.instalar(nombre.strip(), tamano)
        except Exception as error:
            messagebox.showerror("No se pudo instalar", str(error), parent=self.ventana)
            return
        # Muestra la carpeta de programas con el nuevo seleccionado.
        self.ruta = "/programas"
        self.actualizar()
        ruta = f"/programas/{programa['nombre']}"
        if self.tabla.exists(ruta):
            self.tabla.selection_set(ruta)
            self.tabla.see(ruta)
        self.estado.set(f"«{programa['nombre']}» instalado ({tamano} MB). Selecciónalo y pulsa Ejecutar.")

    def leer(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        if elemento["tipo"] == "carpeta":
            self.ir_a(ruta)
            return
        try:
            contenido = self.controlador.leer(ruta)
        except Exception as error:
            messagebox.showerror("No se pudo leer", str(error), parent=self.ventana)
            return
        ventana = tk.Toplevel(self.ventana)
        ventana.title(f"Lectura: {posixpath.basename(ruta)}")
        ventana.geometry("560x380")
        ttk.Label(
            ventana, text="Solo lectura. Para editar, cierra y usa el botón «Modificar».",
            padding=(10, 0, 10, 10),
        ).pack(side="bottom", anchor="w")
        texto = tk.Text(ventana, wrap="word")
        texto.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        texto.insert("1.0", str(contenido))
        texto.configure(state="disabled")

    def modificar(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        if elemento["tipo"] == "carpeta":
            messagebox.showinfo("Modificar archivo", "Selecciona un archivo, no una carpeta.", parent=self.ventana)
            return
        try:
            contenido = self.controlador.leer(ruta)
        except Exception as error:
            messagebox.showerror("No se pudo abrir el archivo", str(error), parent=self.ventana)
            return

        nombre = posixpath.basename(ruta)
        editor = tk.Toplevel(self.ventana)
        editor.title(f"Modificar: {nombre}")
        editor.geometry("620x440")
        editor.minsize(400, 250)

        # La barra de botones se coloca ANTES que el texto y abajo (side="bottom").
        # Si el texto se coloca primero, ocupa toda la ventana y empuja los
        # botones fuera de la vista.
        botones = ttk.Frame(editor, padding=(10, 0, 10, 10))
        botones.pack(side="bottom", fill="x")
        aviso = tk.StringVar(value="Ctrl+S para guardar")
        ttk.Label(botones, textvariable=aviso).pack(side="left")

        caja = tk.Text(editor, wrap="word", undo=True)
        caja.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        caja.insert("1.0", str(contenido))
        caja.edit_modified(False)  # recién abierto: sin cambios pendientes
        caja.focus_set()

        def guardar(_evento: Any = None) -> bool:
            try:
                self.controlador.modificar(ruta, caja.get("1.0", "end-1c"))
            except Exception as error:
                messagebox.showerror("No se pudo guardar", str(error), parent=editor)
                return False
            caja.edit_modified(False)
            editor.title(f"Modificar: {nombre}")
            aviso.set("Cambios guardados")
            self.actualizar()
            self.estado.set(f"Archivo «{nombre}» guardado")
            return True

        def guardar_y_cerrar() -> None:
            if guardar():
                editor.destroy()

        def al_cerrar() -> None:
            # Si hay cambios sin guardar, pregunta antes de cerrar.
            if caja.edit_modified():
                respuesta = messagebox.askyesnocancel(
                    "Cambios sin guardar", f"¿Guardar los cambios en «{nombre}»?", parent=editor
                )
                if respuesta is None:           # Cancelar: sigue editando
                    return
                if respuesta and not guardar():  # Sí, pero falló: no cerrar
                    return
            editor.destroy()

        def al_cambiar(_evento: Any = None) -> None:
            # Un * en el título indica que hay cambios sin guardar.
            if caja.edit_modified():
                editor.title(f"*Modificar: {nombre}")
                aviso.set("Hay cambios sin guardar")

        caja.bind("<<Modified>>", al_cambiar)
        editor.bind("<Control-s>", guardar)
        editor.protocol("WM_DELETE_WINDOW", al_cerrar)
        ttk.Button(botones, text="Cerrar", command=al_cerrar).pack(side="right")
        ttk.Button(botones, text="Guardar y cerrar", command=guardar_y_cerrar).pack(side="right", padx=6)
        ttk.Button(botones, text="Guardar", command=guardar).pack(side="right")

    def eliminar(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        aviso = f"¿Eliminar «{posixpath.basename(ruta)}» del sistema simulado?"
        if elemento["tipo"] == "carpeta":
            aviso += "\n\nSe eliminará también todo lo que contiene."
        if not messagebox.askyesno("Eliminar elemento", aviso, parent=self.ventana):
            return
        try:
            self.controlador.eliminar(ruta)
            self.actualizar()
            self.estado.set(f"«{posixpath.basename(ruta)}» eliminado")
        except Exception as error:
            messagebox.showerror("No se pudo eliminar", str(error), parent=self.ventana)

    def ejecutar(self) -> None:
        # Lanza el archivo como un proceso nuevo del administrador de tareas.
        seleccionado = self._seleccion()
        if seleccionado is None or self.al_ejecutar is None:
            return
        ruta, elemento = seleccionado
        if elemento["tipo"] == "carpeta":
            messagebox.showinfo("Ejecutar", "Selecciona un archivo, no una carpeta.", parent=self.ventana)
            return
        try:
            mensaje = self.al_ejecutar(ruta)
            self.estado.set(mensaje)
            messagebox.showinfo("Archivo ejecutado", mensaje, parent=self.ventana)
        except Exception as error:
            messagebox.showerror("No se pudo ejecutar", str(error), parent=self.ventana)

    def permisos(self) -> None:
        seleccionado = self._seleccion()
        if seleccionado is None:
            return
        ruta, elemento = seleccionado
        actuales = elemento.get("permisos", {})
        es_carpeta = elemento["tipo"] == "carpeta"

        dialogo = tk.Toplevel(self.ventana)
        dialogo.title(f"Permisos: {posixpath.basename(ruta)}")
        dialogo.transient(self.ventana)
        dialogo.grab_set()
        marco = ttk.Frame(dialogo, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text=f"Permisos de «{posixpath.basename(ruta)}»", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))

        # El significado de cada permiso cambia si es archivo o carpeta.
        opciones = (
            ("lectura", "Lectura (r)", "listar su contenido" if es_carpeta else "ver su contenido"),
            ("escritura", "Escritura (w)", "crear y eliminar dentro" if es_carpeta else "modificarlo"),
            ("ejecucion", "Ejecución (x)", "entrar en ella" if es_carpeta else "ejecutarlo"),
        )
        variables: dict[str, tk.BooleanVar] = {}
        for clave, etiqueta, significado in opciones:
            variables[clave] = tk.BooleanVar(value=bool(actuales.get(clave, False)))
            ttk.Checkbutton(marco, text=f"{etiqueta}: {significado}", variable=variables[clave]).pack(anchor="w", pady=2)

        def guardar() -> None:
            try:
                self.controlador.cambiar_permisos(ruta, {clave: variable.get() for clave, variable in variables.items()})
                dialogo.destroy()
                self.actualizar()
                self.estado.set(f"Permisos de «{posixpath.basename(ruta)}» actualizados")
            except Exception as error:
                messagebox.showerror("No se pudieron cambiar los permisos", str(error), parent=dialogo)

        ttk.Button(marco, text="Guardar", command=guardar).pack(anchor="e", pady=(10, 0))
