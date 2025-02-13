import numpy as np
from sqlalchemy.exc import SQLAlchemyError
from db.database import SessionLocal
from models.associations.elemento_circuito import CircuitoElemento
from models.weaks.Circuito import Circuito

def obtener_valores_teoricos(data, etapa_buscada):
    circuitos = data.circuitos

    for circuito in circuitos:
        if circuito.etapa == etapa_buscada:
            return [elemento.existencia_teorica for elemento in circuito.elementos]
    
    return []

def editar_balance_data(data, tms, distribuciones, leyes, contenidos, ensaye_id: int):
    db = SessionLocal()

    try:
        
        #Obtener los circuitos y editar el tms
        circuitos = db.query(Circuito).filter(Circuito.ensaye_id == ensaye_id).all()

        # Normaliza las claves de 'tms' (ejemplo: convertir a mayúsculas y eliminar espacios)
        tms_normalizado = {key.strip().upper(): value for key, value in tms.items()}

        for circuito in circuitos:
            
            # Normaliza la etapa del circuito para que coincida con las claves de 'tms'
            etapa_normalizada = circuito.etapa.strip().upper()
            if etapa_normalizada not in ['COLAS PB', 'COLAS ZN']:
                if etapa_normalizada in tms_normalizado:
                    circuito.tms = float(tms_normalizado[etapa_normalizada])
                else:
                    # Maneja casos donde la etapa no existe en 'tms'
                    raise ValueError(f"Etapa '{circuito.etapa}' no encontrada en el diccionario 'tms'")

        db.commit()
            
        # Obtener los `CircuitoElemento` asociados al ensaye_id
        circuitos_elementos = db.query(CircuitoElemento).filter(
            CircuitoElemento.circuito_ensaye_id == ensaye_id
        ).all()

        for circuito in circuitos_elementos:
            # Asegúrate de convertir los valores a float antes de asignarlos
            circuito.contenido = float(contenidos[circuito.circuito_etapa][circuito.elemento_id - 1])
            circuito.distribucion = float(distribuciones[circuito.circuito_etapa][circuito.elemento_id - 1])
            circuito.ley_corregida = float(leyes[circuito.circuito_etapa][circuito.elemento_id - 1])

        # Confirmar los cambios en la base de datos
        db.commit()

    except SQLAlchemyError as e:
        # En caso de error, hacer rollback y mostrar mensaje de error
        db.rollback()
        print(f"Error al actualizar los datos: {e}")

    finally:
        # Cerrar la sesión
        db.close()
    
def calcular_diferencia(nombre, origen1, origen2, omegas):
    omegas[nombre] = [
        origen1[i] - origen2[i]
        for i in range(len(origen1))
    ]
    
def elevar_omegas(nombre, origen, omegas):
    """
    Eleva cada elemento de la lista `origen` al cuadrado y la almacena en el diccionario `omegas` bajo la clave `nombre`.
    """
    omegas[nombre] = [
        origen[i] ** 2
        for i in range(len(origen))
    ]
    
def suma_producto_numpy(*listas):
    # Convertir las listas en arreglos de NumPy
    arrays = [np.array(lista) for lista in listas]
    
    # Calcular el SUMAPRODUCTO
    producto = np.prod(arrays, axis=0)  # Multiplicación elemento a elemento
    return np.sum(producto)

def procesar_diccionario_y_calcular_inversa(coeficientes, posicion):
    # Inicializar matriz y fila temporal
    matriz = []
    fila = []

    # Iterar sobre las claves del diccionario
    for key in coeficientes:
        # Agregar el elemento en la posición especificada a la fila
        fila.append(coeficientes[key][posicion])

        # Si la fila alcanza 3 elementos, agregarla a la matriz y reiniciar fila
        if len(fila) == 3:
            matriz.append(fila)
            fila = []

    # Agregar los elementos restantes si hay
    if fila:
        matriz.append(fila)

    # Aplicar los cambios de signo
    for i in range(len(matriz)):
        if i == 0:  # Primera fila
            matriz[i][1] = -matriz[i][1]
        elif i == 1:  # Segunda fila
            matriz[i][0] = -matriz[i][0]
            matriz[i][2] = -matriz[i][2]
        elif i == 2:  # Última fila
            matriz[i][1] = -matriz[i][1]

    # Calcular la matriz inversa
    try:
        matriz_np = np.array(matriz)
        matriz_inversa =np.array(np.linalg.inv(matriz_np))
    except np.linalg.LinAlgError:
        # La matriz no es invertible
        matriz_inversa = None

    return matriz, matriz_inversa