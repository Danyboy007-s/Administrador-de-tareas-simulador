#Definición de la clase Tarea y estructuras de datos

class Tarea:
    def __init__(self, id, titulo, completada = False):
        self.id = id
        self.titulo = titulo
        self.completada = completada
        
    def to_dict(self):
        return {"id": self.id, "titulo": self.titulo, "completada": self.completada}
    
    @classmethod
    def from_dict(cls, datos):
        return cls(datos["id"], datos["titulo"], datos["completada"])