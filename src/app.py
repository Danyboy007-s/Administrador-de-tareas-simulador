"""Punto de entrada gráfico del simulador.

Crea la ventana principal, los dos controladores (procesos y archivos) y el
único reloj de la simulación. Las ventanas de views.py reciben los
controladores y solo muestran lo que ellos devuelven.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from src.archivos.controllers import SistemaArchivos
from src.archivos.views import VentanaArchivos
from src.procesos.controllers import AdministradorProcesos
from src.procesos.views import VentanaProcesos


class Aplicacion:
    """Ventana principal; crea controladores y administra el único reloj."""

    def __init__(self, raiz: tk.Tk) -> None:
        self.raiz = raiz
        self.raiz.title("Simulador de administrador de tareas")
        self.raiz.geometry("680x390")
        self.raiz.minsize(560, 330)
        self.procesos = AdministradorProcesos()
        self.archivos = SistemaArchivos()
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
            text="Todo es simulado: los cambios se guardan en data/ y no modifican procesos ni archivos reales.",
            wraplength=580,
        ).pack(anchor="w", pady=(8, 0))

        self.raiz.protocol("WM_DELETE_WINDOW", self.cerrar)
        self._programar_pulso()

    def abrir_procesos(self) -> None:
        if self.ventana_procesos is not None and self.ventana_procesos.existe():
            self.ventana_procesos.traer_al_frente()
            return
        self.ventana_procesos = VentanaProcesos(
            self.raiz, self.procesos,
            al_cerrar=lambda: setattr(self, "ventana_procesos", None),
            al_fallo_critico=self.fallo_critico,
        )

    def fallo_critico(self, proceso: dict) -> None:
        # Se detuvo un proceso crítico: el sistema simulado no puede seguir,
        # igual que si en Windows se detuviera System32 o en Linux el PID 1.
        self._detener_reloj()
        padre = self.ventana_procesos.ventana if self.ventana_procesos is not None else self.raiz
        messagebox.showerror(
            "Fallo crítico del sistema",
            f"Se detuvo «{proceso['nombre']}» (PID {proceso['pid']}), un proceso crítico.\n\n"
            "El sistema no puede continuar y se apagará.\n"
            "Al volver a abrir el programa, el sistema arrancará de nuevo.",
            parent=padre,
        )
        self.cerrar()

    def abrir_archivos(self) -> None:
        if self.ventana_archivos is not None and self.ventana_archivos.existe():
            self.ventana_archivos.traer_al_frente()
            return
        self.ventana_archivos = VentanaArchivos(
            self.raiz, self.archivos,
            al_cerrar=lambda: setattr(self, "ventana_archivos", None),
            al_ejecutar=self.ejecutar_archivo,
        )

    def ejecutar_archivo(self, ruta: str) -> str:
        # Une los dos módulos: procesos/ y archivos/ no se conocen entre sí,
        # así que app.py es quien los coordina.
        # 1. El sistema de archivos revisa el permiso de ejecución.
        archivo = self.archivos.ejecutar(ruta)
        # 2. El administrador crea el proceso. El archivo queda en su BCP como
        #    archivo abierto. Un programa más grande consume más memoria:
        #    usa tantos MB como pesa (mínimo 4 MB, como un script pequeño).
        memoria_mb = max(4, archivo["tamano"] // (1024 * 1024))
        proceso = self.procesos.crear(archivo["nombre"], 5, memoria_mb, archivos_abiertos=[ruta])
        if self.ventana_procesos is not None and self.ventana_procesos.existe():
            self.ventana_procesos.actualizar()
        return (
            f"«{archivo['nombre']}» se cargó como el proceso PID {proceso['pid']}. "
            "Puedes verlo en el Administrador de procesos."
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

    def _detener_reloj(self) -> None:
        if self._after_id is not None:
            try:
                self.raiz.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def cerrar(self) -> None:
        self._detener_reloj()
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
