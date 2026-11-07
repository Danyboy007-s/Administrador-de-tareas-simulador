#Punto de entrada principal para ejecutar el programa
from src.controllers import AdministradorTareas
from src.views import mostrar_menu, mostrar_tareas

def main():
    admin = AdministradorTareas()
    while True:
        opcion = mostrar_menu()
        if opcion == "1":
            admin.agregar(input("Titulo:"))
        elif opcion == "2":
            mostrar_tareas(admin.tarea)
        elif opcion == "0":
            break
        else:
            print("Opcion no valida.")
            
if __name__ == "__main__":
    main()