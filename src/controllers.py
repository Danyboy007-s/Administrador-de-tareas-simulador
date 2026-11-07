#Lógica del negocio (añadir, completar, eliminar tareas)

import json
from pathlib import Path
from src.models import Tarea

RUTA = Path("data/tasks.json")

class AdministradorTareas:
    def __init__(self):
        self.tarea = self.cargar()
        
    def cargar(self):
        texto = RUTA.read_text(encoding="utf-8").strip()
        if not texto: #evita un error si el archivo se encuentra vacio
            return[]
        return[Tarea.from_dict(d) for d in json.loads(texto)]
    
    def guardar (self):
        datos = [t.to_dict() for t in self.tarea]
        RUTA.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        
    def agregar(self, titulo):
        nuevo_id = max((t.id for t in self.tarea), default=0) + 1
        tarea= Tarea(nuevo_id, titulo)
        self.tarea.append(tarea)
        self.guardar()
        return tarea 