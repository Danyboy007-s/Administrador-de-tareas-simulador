#Interdaz del usuario
def mostrar_menu():
    print("\n1. Agregar tarea")
    print("2. Ver tareas")
    print("0. Salir")
    return input ("Elige una opcion: ")

def mostrar_tareas(tarea):
    if not tarea:
        print("No hay tareas.")
    for t in tarea:
        marca = "x" if t.completada else " "
        print(f"[{marca}] {t.id}, {t.titulo}")
        