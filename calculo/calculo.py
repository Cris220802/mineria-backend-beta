import time
import asyncio
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from mail.email import send_notification
import time

from calculo.calculo_helpers import *
from sockets.connection_manager import manager

def calcular_balance(circuitos, ensaye_id):
    tiempo_inicial = time.time()
    print("Iniciando cálculo de ajuste...")
    
    FACTORES_PONDERACION = np.array([10,5,0.1,2.5,2,1.7])
    SD = np.array([0.01, 0.02, 1, 0.04, 0.05, 0.06])
    CABEZA_GENERAL = circuitos.cabeza_general
    
    omegas = {}
    
    cabeza_flotacion = obtener_valores_teoricos(circuitos, "Cabeza Flotacion")
    concentrado_pb = obtener_valores_teoricos(circuitos, "Concentrado Pb")
    colas_pb = obtener_valores_teoricos(circuitos, "Colas Pb")
    concentrado_zn = obtener_valores_teoricos(circuitos, "Concentrado Zn")
    colas_zn = obtener_valores_teoricos(circuitos, "Colas Zn")
    concentrado_fe = obtener_valores_teoricos(circuitos, "Concentrado Fe")
    colas_finales = obtener_valores_teoricos(circuitos, "Colas Finales")
    
    calcular_diferencia('uno_Dos', cabeza_flotacion, concentrado_pb, omegas)
    calcular_diferencia('dos_Tres', concentrado_pb, colas_pb, omegas)
    calcular_diferencia('tres_Cinco', colas_pb, colas_zn, omegas)
    calcular_diferencia('cuatro_Cinco', concentrado_zn, colas_zn, omegas)
    calcular_diferencia('cinco_Siete', colas_zn, colas_finales, omegas)
    calcular_diferencia('seis_Siete', concentrado_fe, colas_finales, omegas)
    
    elevar_omegas('dos_Tres_Cuadrado', omegas['dos_Tres'], omegas)
    elevar_omegas('tres_Cinco_Cuadrado', omegas['tres_Cinco'], omegas)
    elevar_omegas('cuatro_Cinco_Cuadrado', omegas['cuatro_Cinco'], omegas)
    elevar_omegas('cinco_Siete_Cuadrado', omegas['cinco_Siete'], omegas)
    elevar_omegas('seis_Siete_Cuadrado', omegas['seis_Siete'], omegas)


    Fi ={'Uno': 1}
    
    matriz = {}

    producto_1 = suma_producto_numpy(FACTORES_PONDERACION, omegas['dos_Tres_Cuadrado'])
    producto_2 = suma_producto_numpy(FACTORES_PONDERACION, omegas['tres_Cinco_Cuadrado'])
    producto_3 = suma_producto_numpy(FACTORES_PONDERACION, omegas['cinco_Siete_Cuadrado'])
    producto_4 = suma_producto_numpy(FACTORES_PONDERACION, omegas['tres_Cinco'], omegas['cuatro_Cinco'])
    producto_5 = suma_producto_numpy(FACTORES_PONDERACION, omegas['cinco_Siete'], omegas['seis_Siete'])
    producto_6 = suma_producto_numpy(FACTORES_PONDERACION, omegas['cuatro_Cinco_Cuadrado'])
    
    matriz = {
        'fila_1': [
            (producto_1 + producto_2 + producto_3),
            -(producto_4 + producto_3),
            -(producto_5)
        ],
        'fila_2': [
            -(producto_4 + producto_3),
            (producto_6 + producto_3),
            producto_5
        ],
        'fila_3': [
            -(producto_5),
            producto_5,
            suma_producto_numpy(FACTORES_PONDERACION, omegas['seis_Siete_Cuadrado'])
        ]
    }

    terminosInd = np.array([[suma_producto_numpy(FACTORES_PONDERACION, omegas['uno_Dos'], omegas['dos_Tres'])], [0], [0]])

    matriz_a_invertir = np.array([matriz['fila_1'], matriz['fila_2'], matriz['fila_3']])

    # Intentar calcular la matriz inversa
    try:
        matriz_inversa = np.array(np.linalg.inv(matriz_a_invertir))
        
    except np.linalg.LinAlgError:
        print("La matriz no es invertible (determinante es cero).")

    Fi_3_4_6 = -(np.dot(matriz_inversa, terminosInd))

    Fi['Dos'] = Fi['Uno'] - Fi_3_4_6[0].item()
    Fi['Tres'] = Fi_3_4_6[0].item()
    Fi['Cuatro'] = Fi_3_4_6[1].item()
    Fi['Cinco'] = Fi['Tres'] - Fi['Cuatro']
    Fi['Seis'] = Fi_3_4_6[2].item()
    Fi['Siete'] = Fi['Cinco'] - Fi['Seis']
    
    distribution_Contenidos ={}

    distribution_Contenidos['X1'] = [
        ((Fi['Uno'] * cabeza_flotacion[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['X2'] = [
        ((Fi['Dos'] * concentrado_pb[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['X3'] = [
        ((Fi['Tres'] * colas_pb[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['X4'] = [
        ((Fi['Cuatro'] * concentrado_zn[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['X5'] = [
        ((Fi['Cinco'] * colas_zn[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['X6'] = [
        ((Fi['Seis'] * concentrado_fe[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['X7'] = [
        ((Fi['Siete'] * colas_finales[i]) / (cabeza_flotacion[i] * Fi['Uno'])) * 100
        for i in range(len(cabeza_flotacion))    
    ]

    distribution_Contenidos['Error'] = [
        distribution_Contenidos['X1'][i] - distribution_Contenidos['X2'][i] - distribution_Contenidos['X4'][i] - distribution_Contenidos['X6'][i] - distribution_Contenidos['X7'][i]
        for i in range(len(distribution_Contenidos['X1']))
    ]

    # Errores en las leyes DELTAS
    errores_Deltas = {}

    errores_Deltas['Delta_1'] = [
        cabeza_flotacion[i] - (concentrado_pb[i] * Fi['Dos'] +colas_pb[i] * Fi['Tres'])
        for i in range(len(cabeza_flotacion))
    ]

    errores_Deltas['Delta_2'] = [
       colas_pb[i] * Fi['Tres'] - (concentrado_zn[i] * Fi['Cuatro'] + colas_zn[i] * Fi['Cinco'])
        for i in range(len(cabeza_flotacion))
    ]

    errores_Deltas['Delta_3'] = [
        colas_zn[i] * Fi['Cinco'] - (concentrado_fe[i] * Fi['Seis'] + colas_finales[i] * Fi['Siete'])
        for i in range(len(cabeza_flotacion))
    ]
    
    # Factores de ponderacion Wi
    factores_Ponderacion_Wi = {}

    factores_Ponderacion_Wi['X1'] = [
        1000000 / ((cabeza_flotacion[0] * (100 - cabeza_flotacion[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((cabeza_flotacion[1] * (100 - cabeza_flotacion[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((cabeza_flotacion[i] * (100 - cabeza_flotacion[i])) ** 2) / SD[i]
            for i in range(2, len(cabeza_flotacion))  # Resto de los elementos
        ]
    ]

    factores_Ponderacion_Wi['X2'] = [
        1000000 / ((concentrado_pb[0] * (100 - concentrado_pb[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((concentrado_pb[1] * (100 - concentrado_pb[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((concentrado_pb[i] * (100 - concentrado_pb[i])) ** 2) / SD[i]
            for i in range(2, len(concentrado_pb))  # Resto de los elementos
        ]
    ]

    factores_Ponderacion_Wi['X3'] = [
        1000000 / ((colas_pb[0] * (100 - colas_pb[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((colas_pb[1] * (100 - colas_pb[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((colas_pb[i] * (100 - colas_pb[i])) ** 2) / SD[i]
            for i in range(2, len(colas_pb))  # Resto de los elementos
        ]
    ]

    factores_Ponderacion_Wi['X4'] = [
        1000000 / ((concentrado_zn[0] * (100 - concentrado_zn[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((concentrado_zn[1] * (100 - concentrado_zn[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((concentrado_zn[i] * (100 - concentrado_zn[i])) ** 2) / SD[i]
            for i in range(2, len(concentrado_zn))  # Resto de los elementos
        ]
    ]

    factores_Ponderacion_Wi['X5'] = [
        1000000 / ((colas_zn[0] * (100 - colas_zn[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((colas_zn[1] * (100 - colas_zn[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((colas_zn[i] * (100 - colas_zn[i])) ** 2) / SD[i]
            for i in range(2, len(colas_zn))  # Resto de los elementos
        ]
    ]

    factores_Ponderacion_Wi['X6'] = [
        1000000 / ((concentrado_fe[0] * (100 - concentrado_fe[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((concentrado_fe[1] * (100 - concentrado_fe[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((concentrado_fe[i] * (100 - concentrado_fe[i])) ** 2) / SD[i]
            for i in range(2, len(concentrado_fe))  # Resto de los elementos
        ]
    ]

    factores_Ponderacion_Wi['X7'] = [
        1000000 / ((colas_finales[0] * (100 - colas_finales[0])) ** 2) / SD[0],  # Primer elemento
        1000000 / ((colas_finales[1] * (100 - colas_finales[1])) ** 2) / SD[1],  # Segundo elemento
        *[
            100 / ((colas_finales[i] * (100 - colas_finales[i])) ** 2) / SD[i]
            for i in range(2, len(colas_finales))  # Resto de los elementos
        ]
    ]

    # Coeficientes A, B, C

    coeficientes = {}

    coeficientes['A1'] = [
        (1 / factores_Ponderacion_Wi['X1'][i]) + (Fi['Dos']**2 / factores_Ponderacion_Wi['X2'][i]) + (Fi['Tres']**2 / factores_Ponderacion_Wi['X3'][i])
        for i in range(len(factores_Ponderacion_Wi['X1']))
    ]

    coeficientes['B1'] = [
        Fi['Tres']**2 / factores_Ponderacion_Wi['X3'][i]
        for i in range(len(factores_Ponderacion_Wi['X3']))
    ]

    coeficientes['C1'] = [
        0
        for i in range(len(factores_Ponderacion_Wi['X3']))
    ]

    coeficientes['A2'] = coeficientes['B1']

    coeficientes['B2'] = [
        (Fi['Tres']**2 / factores_Ponderacion_Wi['X3'][i]) + (Fi['Cuatro']**2 / factores_Ponderacion_Wi['X4'][i]) + (Fi['Cinco']**2 / factores_Ponderacion_Wi['X5'][i])
        for i in range(len(factores_Ponderacion_Wi['X3']))
    ]

    coeficientes['C2'] = [
        Fi['Cinco']**2 / factores_Ponderacion_Wi['X5'][i]
        for i in range(len(factores_Ponderacion_Wi['X5']))
    ]

    coeficientes['A3'] = [
        0
        for i in range(len(factores_Ponderacion_Wi['X3']))
    ]

    coeficientes['B3'] = coeficientes['C2']

    coeficientes['C3'] = [
        Fi['Cinco']**2 / factores_Ponderacion_Wi['X5'][i] + Fi['Seis']**2 / factores_Ponderacion_Wi['X6'][i] + Fi['Siete']**2 / factores_Ponderacion_Wi['X7'][i]
        for i in range(len(factores_Ponderacion_Wi['X3']))
    ]
    
    # Generar matriz y su inversa para la posición 0
    matrizA_Cu, matriz_inversaA_Cu = procesar_diccionario_y_calcular_inversa(coeficientes, 0)
    matrizA_Zn, matriz_inversaA_Zn = procesar_diccionario_y_calcular_inversa(coeficientes, 1)
    matrizA_Ag, matriz_inversaA_Ag = procesar_diccionario_y_calcular_inversa(coeficientes, 2)
    matrizA_Bi, matriz_inversaA_Bi = procesar_diccionario_y_calcular_inversa(coeficientes, 3)
    matrizA_Mo, matriz_inversaA_Mo = procesar_diccionario_y_calcular_inversa(coeficientes, 4)
    matrizA_Fe, matriz_inversaA_Fe = procesar_diccionario_y_calcular_inversa(coeficientes, 5)

    # terminos Independientes
    dicc_TermIndependientes ={}

    dicc_TermIndependientes['Cu'] = [[-2*errores_Deltas['Delta_1'][0]], [-2*errores_Deltas['Delta_2'][0]], [-2*errores_Deltas['Delta_3'][0]]]
    dicc_TermIndependientes['Zn'] = [[-2*errores_Deltas['Delta_1'][1]], [-2*errores_Deltas['Delta_2'][1]], [-2*errores_Deltas['Delta_3'][1]]]
    dicc_TermIndependientes['Ag'] = [[-2*errores_Deltas['Delta_1'][2]], [-2*errores_Deltas['Delta_2'][2]], [-2*errores_Deltas['Delta_3'][2]]]
    dicc_TermIndependientes['Bi'] = [[-2*errores_Deltas['Delta_1'][3]], [-2*errores_Deltas['Delta_2'][3]], [-2*errores_Deltas['Delta_3'][3]]]
    dicc_TermIndependientes['Mo'] = [[-2*errores_Deltas['Delta_1'][4]], [-2*errores_Deltas['Delta_2'][4]], [-2*errores_Deltas['Delta_3'][4]]]
    dicc_TermIndependientes['Fe'] = [[-2*errores_Deltas['Delta_1'][5]], [-2*errores_Deltas['Delta_2'][5]], [-2*errores_Deltas['Delta_3'][5]]]

    dicc_Soluciones = {}

    dicc_Soluciones['Cu'] = np.dot(matriz_inversaA_Cu, dicc_TermIndependientes['Cu'])
    dicc_Soluciones['Zn'] = np.dot(matriz_inversaA_Zn, dicc_TermIndependientes['Zn'])
    dicc_Soluciones['Ag'] = np.dot(matriz_inversaA_Ag, dicc_TermIndependientes['Ag'])
    dicc_Soluciones['Bi'] = np.dot(matriz_inversaA_Bi, dicc_TermIndependientes['Bi'])
    dicc_Soluciones['Mo'] = np.dot(matriz_inversaA_Mo, dicc_TermIndependientes['Mo'])
    dicc_Soluciones['Fe'] = np.dot(matriz_inversaA_Fe, dicc_TermIndependientes['Fe'])

    lambdas = {}

    lambdas['lambda_1'] = [
        dicc_Soluciones[key][0].item()
        for key in dicc_Soluciones
    ]

    lambdas['lambda_2'] = [
        dicc_Soluciones[key][1].item()
        for key in dicc_Soluciones
    ]

    lambdas['lambda_3'] = [
        dicc_Soluciones[key][2].item()
        for key in dicc_Soluciones
    ]

    # Factores de Correccion de leyes

    factores_Correccion = {}

    factores_Correccion['X1'] = [
        (-1 / 2) * (lambdas['lambda_1'][i] / factores_Ponderacion_Wi['X1'][i])
        for i in range(len(lambdas['lambda_1']))
    ]

    factores_Correccion['X2'] = [
        (1 / 2) * (lambdas['lambda_1'][i]) * (Fi['Dos'] / factores_Ponderacion_Wi['X2'][i])
        for i in range(len(lambdas['lambda_1']))
    ]

    factores_Correccion['X3'] = [
        (1 / 2) * (lambdas['lambda_1'][i] - lambdas['lambda_2'][i]) * ( Fi['Tres'] / factores_Ponderacion_Wi['X3'][i])
        for i in range(len(lambdas['lambda_1']))
    ]

    factores_Correccion['X4'] = [
        (0.5) * (lambdas['lambda_2'][i]) * ( Fi['Cuatro'] / factores_Ponderacion_Wi['X4'][i])
        for i in range(len(lambdas['lambda_1']))
    ]

    factores_Correccion['X5'] = [
        (0.5) * ((lambdas['lambda_2'][i] - lambdas['lambda_3'][i]) / factores_Ponderacion_Wi['X5'][i]) * Fi['Cinco']
        for i in range(len(lambdas['lambda_1']))
    ]

    factores_Correccion['X6'] = [
        (0.5) * (lambdas['lambda_3'][i] / factores_Ponderacion_Wi['X6'][i]) * Fi['Seis']
        for i in range(len(lambdas['lambda_1']))
    ]

    factores_Correccion['X7'] = [
        (0.5) * (lambdas['lambda_3'][i]) * ( Fi['Siete'] / factores_Ponderacion_Wi['X7'][i])
        for i in range(len(lambdas['lambda_1']))
    ]

    leyes_Corregidas = {}

    leyes_Corregidas['X1'] = [
        cabeza_flotacion[i] - factores_Correccion['X1'][i]
        for i in range(len(cabeza_flotacion))
    ]

    leyes_Corregidas['X2'] = [
        concentrado_pb[i] - factores_Correccion['X2'][i]
        for i in range(len(concentrado_pb))
    ]

    leyes_Corregidas['X3'] = [
        colas_pb[i] - factores_Correccion['X3'][i]
        for i in range(len(colas_pb))
    ]

    leyes_Corregidas['X4'] = [
        concentrado_zn[i] - factores_Correccion['X4'][i]
        for i in range(len(concentrado_zn))
    ]

    leyes_Corregidas['X5'] = [
        colas_zn[i] - factores_Correccion['X5'][i]
        for i in range(len(colas_zn))
    ]

    leyes_Corregidas['X6'] = [
        concentrado_fe[i] - factores_Correccion['X6'][i]
        for i in range(len(concentrado_fe))
    ]

    leyes_Corregidas['X7'] = [
        colas_finales[i] - factores_Correccion['X7'][i]
        for i in range(len(colas_finales))
    ]

    dContenidos_Corregidos = {}

    dContenidos_Corregidos['X1'] = [
        (leyes_Corregidas['X1'][i] * Fi['Uno']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['X2'] = [
        (leyes_Corregidas['X2'][i] * Fi['Dos']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['X3'] = [
        (leyes_Corregidas['X3'][i] * Fi['Tres']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['X4'] = [
        (leyes_Corregidas['X4'][i] * Fi['Cuatro']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['X5'] = [
        (leyes_Corregidas['X5'][i] * Fi['Cinco']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['X6'] = [
        (leyes_Corregidas['X6'][i] * Fi['Seis']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['X7'] = [
        (leyes_Corregidas['X7'][i] * Fi['Siete']) / (leyes_Corregidas['X1'][i] * Fi['Uno']) * 100
        for i in range(len(leyes_Corregidas['X1']))
    ]

    dContenidos_Corregidos['Error'] = [
        round(dContenidos_Corregidos['X1'][i] - dContenidos_Corregidos['X2'][i] - dContenidos_Corregidos['X4'][i] - dContenidos_Corregidos['X6'][i] - dContenidos_Corregidos['X7'][i], 6)
        for i in range(len(leyes_Corregidas['X1']))
    ]

    solidos_Corregido = {}

    solidos_Corregido['X1'] = round(CABEZA_GENERAL * Fi['Uno'], 2)
    solidos_Corregido['X2'] = round(CABEZA_GENERAL * Fi['Dos'], 2)
    solidos_Corregido['X3'] = round(CABEZA_GENERAL * Fi['Tres'], 2)
    solidos_Corregido['X4'] = round(CABEZA_GENERAL * Fi['Cuatro'], 2)
    solidos_Corregido['X5'] = round(CABEZA_GENERAL * Fi['Cinco'], 2)
    solidos_Corregido['X6'] = round(CABEZA_GENERAL * Fi['Seis'], 2)
    solidos_Corregido['X7'] = round(CABEZA_GENERAL * Fi['Siete'], 2)
    
    ################ BALANCE ##################

    insoluble = [12, 15, 16]
    cabeza_Calculada = round(solidos_Corregido['X2'] + solidos_Corregido['X4'] + solidos_Corregido['X6'] + solidos_Corregido['X7'], 4)
    # Lista de claves que deseas usar
    claves_deseadas = ['X1', 'X2', 'X4', 'X6', 'X7']

    distribucion = {}

    distribucion['Cabeza Flotacion'] = dContenidos_Corregidos['X1']
    distribucion['Concentrado Pb'] = dContenidos_Corregidos['X2']
    distribucion['Colas Pb'] = dContenidos_Corregidos['X3']
    distribucion['Concentrado Zn'] = dContenidos_Corregidos['X4']
    distribucion['Colas Zn'] = dContenidos_Corregidos['X5']
    distribucion['Concentrado Fe'] = dContenidos_Corregidos['X6']
    distribucion['Colas Finales'] = dContenidos_Corregidos['X7']
    distribucion['Cabeza_Calculada'] = [
        round(distribucion['Concentrado Pb'][i] + distribucion['Concentrado Zn'][i] + distribucion['Concentrado Fe'][i] + distribucion['Colas Finales'][i], 2)
        for i in range(len(distribucion['Cabeza Flotacion']))
    ]

    tsm = [
        CABEZA_GENERAL, solidos_Corregido['X2'], solidos_Corregido['X4'], solidos_Corregido['X6'], solidos_Corregido['X7'], cabeza_Calculada
    ]
    tms = {}
    tms['Cabeza Flotacion'] = CABEZA_GENERAL
    tms['Concentrado Pb'] = solidos_Corregido['X2']
    tms['Concentrado Zn'] = solidos_Corregido['X4']
    tms['Concentrado Fe'] = solidos_Corregido['X6']
    tms['Colas Finales'] = solidos_Corregido['X7']
    tms['Cabeza Calculada'] = cabeza_Calculada

    ensayes = {}

    ensayes['Cabeza Flotacion'] = leyes_Corregidas['X1']
    ensayes['Concentrado Pb'] = leyes_Corregidas['X2']
    ensayes['Colas Pb'] = leyes_Corregidas['X3']
    ensayes['Concentrado Zn'] = leyes_Corregidas['X4']
    ensayes['Colas Zn'] = leyes_Corregidas['X5']
    ensayes['Concentrado Fe'] = leyes_Corregidas['X6']
    ensayes['Colas Finales'] = leyes_Corregidas['X7']

    contenidos = {}

    contenidos['Cabeza Flotacion'] = [
        (tsm[0] * ensayes['Cabeza Flotacion'][0]) / 1000,
        (tsm[0] * ensayes['Cabeza Flotacion'][1]) / 1000,
        *[
            (tsm[0] * ensayes['Cabeza Flotacion'][i]) / 100
            for i in range(2, len(ensayes['Cabeza Flotacion']))
        ]
    ]

    contenidos['Concentrado Pb'] = [
        (contenidos['Cabeza Flotacion'][i] * distribucion['Concentrado Pb'][i]) / 100
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]
    
    contenidos['Colas Pb'] = [
        (contenidos['Cabeza Flotacion'][i] * distribucion['Colas Pb'][i]) / 100
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]

    contenidos['Concentrado Zn'] = [
        (contenidos['Cabeza Flotacion'][i] * distribucion['Concentrado Zn'][i]) / 100
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]
    
    contenidos['Colas Zn'] = [
        (contenidos['Cabeza Flotacion'][i] * distribucion['Colas Zn'][i]) / 100
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]

    contenidos['Concentrado Fe'] = [
        (contenidos['Cabeza Flotacion'][i] * distribucion['Concentrado Fe'][i]) / 100
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]

    contenidos['Colas Finales'] = [
        (contenidos['Cabeza Flotacion'][i] * distribucion['Colas Finales'][i]) / 100
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]

    contenidos['Cabeza_Calculada'] = [
        contenidos['Concentrado Pb'][i] + contenidos['Concentrado Zn'][i] + contenidos['Concentrado Fe'][i] + contenidos['Colas Finales'][i]
        for i in range(len(contenidos['Cabeza Flotacion']))
    ]

    insoluble_Contenidos = [
        (tsm[i] * insoluble[i]) / 100
        for i in range(len(insoluble))
    ]

    ensayes['Cabeza_Calculada'] = [
        (contenidos['Cabeza_Calculada'][0] * 1000) / tsm[5],
        (contenidos['Cabeza_Calculada'][1] * 1000) / tsm[5],
        *[
            (contenidos['Cabeza_Calculada'][i] * 100) / tsm[5]
            for i in range(2, len(contenidos['Cabeza_Calculada']))
        ]
    ]
    
    tiempo_final = time.time() - tiempo_inicial
    
    # Actualizar data en base de datos
    editar_balance_data(data=circuitos, tms=tms, distribuciones=distribucion, contenidos=contenidos, leyes=ensayes, ensaye_id=ensaye_id)
    
    print(f"Tiempo de ejecución: {tiempo_final:.6f} segundos")
    print("Cálculo finalizado")
    return True

async def ejecutar_calculo_lagrange(users, essay_id, essay_date, essay_shift, circuitos):
    loop = asyncio.get_event_loop()
    ensaye_id_str = str(essay_id)
    try:
        with ProcessPoolExecutor() as pool:
            print(f"[{ensaye_id_str}] Iniciando cálculo de balance en ProcessPoolExecutor...")
            # Asegúrate que 'circuitos_request_data' y 'essay_id' sean picklables para ProcessPoolExecutor
            # 'calcular_balance' es tu función síncrona y pesada
            resultado_calculo = await loop.run_in_executor(pool, calcular_balance, circuitos, essay_id)
            print(f"[{ensaye_id_str}] Cálculo de balance finalizado. Resultado: {resultado_calculo}")

        if resultado_calculo: # Asume que True o un objeto evaluado como True significa éxito
            await manager.send_status_update(
                ensaye_id_str,
                "balance_calculation_finished",
                "Cálculo de balance finalizado exitosamente.",
                success=True
            )

            # Ahora, enviar el email
            usuarios_validos = [user for user in users if user.rol_id != 4] # Asumiendo que 'users' son tus objetos User con 'rol_id'
            
            email_enviado_exitosamente = await send_notification(
                usuarios_validos, essay_id, essay_date, essay_shift
            )

            if email_enviado_exitosamente:
                await manager.send_status_update(
                    ensaye_id_str,
                    "email_notification_sent",
                    "Notificación por correo enviada exitosamente.",
                    success=True
                )
            else:
                await manager.send_status_update(
                    ensaye_id_str,
                    "email_notification_sent",
                    "Error al enviar la notificación por correo.",
                    success=False
                )
        else:
            # El cálculo de balance falló
            await manager.send_status_update(
                ensaye_id_str,
                "balance_calculation_finished",
                "Error durante el cálculo de balance.",
                success=False
            )
            # Opcionalmente, indicar que el email no se envió debido a esto
            await manager.send_status_update(
                ensaye_id_str,
                "email_notification_sent",
                "Envío de correo omitido debido a error en cálculo de balance.",
                success=False, # O un estado "skipped" si prefieres
                data={"reason": "balance_calculation_failed"}
            )

    except Exception as e:
        print(f"Error general en la tarea de fondo para ensaye {ensaye_id_str}: {e}")
        await manager.send_status_update(
            ensaye_id_str,
            "background_task_error",
            f"Error inesperado durante el procesamiento en segundo plano: {str(e)}",
            success=False
        )

                
            
            