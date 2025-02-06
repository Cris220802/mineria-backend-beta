import numpy as np

def obtener_valores_teoricos(data, etapa_buscada):
    circuitos = data.circuitos

    for circuito in circuitos:
        if circuito.etapa == etapa_buscada:
            return [elemento.existencia_teorica for elemento in circuito.elementos]
    
    return []

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