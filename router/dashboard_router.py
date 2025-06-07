from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.orm import joinedload
from sqlalchemy import func, and_
from datetime import date, timedelta
from typing import List, Optional

from schemas.dashboard_schema import DashboardResponse, ResumenElemento, RecuperacionElemento, ElementoValorRecuperacion, ElementoValorContenido, ContenidoElemento, ElementoValorLey, LeyElemento, CalidadConcentrado, CalidadesConcentrados
from schemas.ensaye_schema import EnsayeResponse
from db.database import db_dependency
from auth.auth import permission_required
from models.Ensaye import Ensaye
from models.Elemento import Elemento
from models.weaks.Circuito import Circuito
from models.associations.elemento_circuito import CircuitoElemento, Etapa

router = APIRouter(
    prefix="/dashboard",
    tags=['dashboard']
)

@router.get("/")
async def get_dashboard(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
):
    # El try-except externo aquí es para errores en la orquestación misma del endpoint get_dashboard,
    # no para los errores de obtención de datos de las sub-funciones, que _fetch_dashboard_part_safely maneja.
    try:
        resumen_data = _fetch_dashboard_part_safely(get_element_resume, db=db)
        recuperaciones_data = _fetch_dashboard_part_safely(get_recuperaciones, db=db)
        contenidos_data = _fetch_dashboard_part_safely(get_contenidos, db=db)
        leyes_data = _fetch_dashboard_part_safely(get_leyes, db=db)
        # Para get_ensayes, si no tiene parámetros obligatorios por defecto para el dashboard general:
        ensayes_data = _fetch_dashboard_part_safely(get_ensayes_dia, db=db) # Ajusta parámetros si es necesario

        return {
            "resumen": resumen_data,
            "recuperaciones": recuperaciones_data,
            "contenidos": contenidos_data,
            "leyes": leyes_data,
            "ensayes_dia": ensayes_data
        }
    except Exception as e:
        # Este error es si algo falla en la lógica del endpoint get_dashboard mismo,
        # fuera de las llamadas a _fetch_dashboard_part_safely.
        print(f"Error crítico al ensamblar el dashboard principal: {type(e).__name__} - {e}")
        raise HTTPException(status_code=500, detail="Ocurrió un error interno general al generar el dashboard.")

@router.get("/resumen")
async def get_resumen(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
    init_date: Optional[str] = Query(None, alias="initial date", description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, alias="final date", description="Fecha final de busqueda (opcional)"),
):
    try:
        resumen = get_element_resume(init_date=init_date, final_date=final_date, db=db)
        
        return {
            "resumen": resumen
        }
    except HTTPException as he:
        # Si get_element_resume (o cualquier lógica aquí) lanza una HTTPException,
        # la relanzamos para que FastAPI la maneje con su código y detalle originales.
        raise he
    except Exception as e:
        # Para cualquier otra excepción inesperada.
        print(f"Error inesperado en /dashboard/resumen: {type(e).__name__} - {e}") # Log del error en el servidor
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al procesar el resumen.")
    
@router.get("/recuperaciones")
async def get_recuperaciones(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
    init_date: Optional[str] = Query(None, alias="initial date", description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, alias="final date", description="Fecha final de busqueda (opcional)"),
    elements: Optional[List[int]] = Query(None, description="Lista de elementos para filtrar (opcional)")
):
    try:
        recuperaciones = get_recuperaciones(init_date=init_date, final_date=final_date, elements=elements, db=db)
        
        return {
            "recuperaciones": recuperaciones
        }
    except HTTPException as he:
        # Si get_element_resume (o cualquier lógica aquí) lanza una HTTPException,
        # la relanzamos para que FastAPI la maneje con su código y detalle originales.
        raise he
    except Exception as e:
        # Para cualquier otra excepción inesperada.
        print(f"Error inesperado en /dashboard/recuperaciones: {type(e).__name__} - {e}") # Log del error en el servidor
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al procesar el resumen.")

@router.get("/contenidos")
async def get_contenidos(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
    init_date: Optional[str] = Query(None, alias="initial date", description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, alias="final date", description="Fecha final de busqueda (opcional)"),
    elements: Optional[List[int]] = Query(None, description="Lista de elementos para filtrar (opcional)")
):
    try:
        contenidos = get_contenidos(init_date=init_date, final_date=final_date, elements=elements, db=db)
        
        return {
            "contenidos": contenidos
        }
    except HTTPException as he:
        # Si get_element_resume (o cualquier lógica aquí) lanza una HTTPException,
        # la relanzamos para que FastAPI la maneje con su código y detalle originales.
        raise he
    except Exception as e:
        # Para cualquier otra excepción inesperada.
        print(f"Error inesperado en /dashboard/contenidos: {type(e).__name__} - {e}") # Log del error en el servidor
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al procesar el resumen.")
     
@router.get("/leyes")
async def get_leyes(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
    init_date: Optional[str] = Query(None, alias="initial date", description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, alias="final date", description="Fecha final de busqueda (opcional)"),
    etapas: Optional[List[str]] = Query(None, description="Lista de etapas para filtrar (opcional)")
):
    try:
        leyes = get_leyes(init_date=init_date, final_date=final_date, db=db, etapas=etapas)
        
        return {
            "leyes": leyes
        }
    except HTTPException as he:
        # Si get_element_resume (o cualquier lógica aquí) lanza una HTTPException,
        # la relanzamos para que FastAPI la maneje con su código y detalle originales.
        raise he
    except Exception as e:
        # Para cualquier otra excepción inesperada.
        print(f"Error inesperado en /dashboard/leyes: {type(e).__name__} - {e}") # Log del error en el servidor
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al procesar el resumen.")
    
@router.get("/ensayes")
async def get_ensayes(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
    init_date: Optional[str] = Query(None, alias="initial date", description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, alias="final date", description="Fecha final de busqueda (opcional)"),
    user_id: Optional[int] = Query(None, alias="user id", description="Usuario del id"),
    skip: int = Query(0, alias="page", description="Número de página (0 por defecto)"),
    limit: int = Query(5, le=10, description="Cantidad de registros por página (máx. 10)")
):
    try:
        ensayes = get_ensayes(init_date=init_date, final_date=final_date, user_id=user_id, skip=skip, limit=limit, db=db)
        
        return {
            "ensayes": ensayes
        }
    except HTTPException as he:
        # Si get_element_resume (o cualquier lógica aquí) lanza una HTTPException,
        # la relanzamos para que FastAPI la maneje con su código y detalle originales.
        raise he
    except Exception as e:
        # Para cualquier otra excepción inesperada.
        print(f"Error inesperado en /dashboard/leyes: {type(e).__name__} - {e}") # Log del error en el servidor
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al procesar el resumen.")
    
@router.get("/ensaye/dia")
async def get_ensayes_dia(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta")),
):
    try:
        ensayes = get_ensayes_dia(db=db)
        
        return {
            "ensayes_dia": ensayes
        }
    except HTTPException as he:
        # Si get_element_resume (o cualquier lógica aquí) lanza una HTTPException,
        # la relanzamos para que FastAPI la maneje con su código y detalle originales.
        raise he
    except Exception as e:
        # Para cualquier otra excepción inesperada.
        print(f"Error inesperado en /dashboard/leyes: {type(e).__name__} - {e}") # Log del error en el servidor
        raise HTTPException(status_code=500, detail="Ocurrió un error interno inesperado al procesar el resumen.")
    return
    
def get_element_resume(init_date=None, final_date=None, db=db_dependency):
    today = date.today()

    # Obtener el rango de fechas
    if init_date and final_date:
        try:
            init_date = date.fromisoformat(init_date)
            final_date = date.fromisoformat(final_date)
        except Exception as e:
            print(e)
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")
        
        past_init_date = init_date - (final_date - init_date) - timedelta(days=1)
        past_final_date = init_date - timedelta(days=1)
    else:
        init_date = today
        final_date = today
        print(f"DEBUG: date.today() utilizada como init_date: {init_date}, final_date: {final_date}") # <-- AÑADE ESTO
        past_init_date = today - timedelta(days=1)
        past_final_date = today - timedelta(days=1)
        
    # Obtener los ensayes actuales
    ensayes = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= init_date,
        func.date(Ensaye.fecha) <= final_date
    ).all()

    print(ensayes)
    if not ensayes:
        raise HTTPException(status_code=400, detail="No se encontraron ensayes en las fechas seleccionadas.")

    # Obtener los ensayes anteriores para comparativa
    past_ensayes = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= past_init_date,
        func.date(Ensaye.fecha) <= past_final_date
    ).all()

    elementos = db.query(Elemento).all()

    ensayes_ids = [ensaye.id for ensaye in ensayes]
    past_ensayes_ids = [ensaye.id for ensaye in past_ensayes]
    etapas = ["CONCPB", "CONCZN", "CONCFE"]

    # Circuitos actuales
    circuitos = db.query(CircuitoElemento).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(ensayes_ids),
            CircuitoElemento.circuito_etapa.in_(etapas)
        )
    ).all()

    # Circuitos pasados
    past_circuitos = db.query(CircuitoElemento).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(past_ensayes_ids),
            CircuitoElemento.circuito_etapa.in_(etapas)
        )
    ).all()

    if not circuitos:
        raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al intentar obtener los circuitos actuales.")

    resumen = []

    for elemento in elementos:
        new_resume = ResumenElemento()
        new_resume.elemento = elemento.name
        new_resume.recuperacion = 0
        new_resume.contenido = 0
        new_resume.ley = 0
        past_resume = ResumenElemento()
        past_resume.recuperacion = 0
        past_resume.contenido = 0
        past_resume.ley = 0

        for circuito in circuitos:
            if elemento.id == circuito.elemento_id:
                new_resume.recuperacion += circuito.distribucion or 0
                new_resume.contenido += circuito.contenido or 0
                if circuito.circuito_etapa == Etapa.CONCPB and elemento.name in ["Pb", "Ag", "Zn"]:
                    new_resume.ley += circuito.ley_corregida or 0
                elif circuito.circuito_etapa == Etapa.CONCZN and elemento.name in ["Ag", "Zn"]:
                    new_resume.ley += circuito.ley_corregida or 0
                elif circuito.circuito_etapa == Etapa.CONCFE and elemento.name in ["Ag", "Au", "Fe"]:
                    new_resume.ley += circuito.ley_corregida or 0

        for circuito in past_circuitos:
            if elemento.id == circuito.elemento_id:
                past_resume.recuperacion += circuito.distribucion or 0
                past_resume.contenido += circuito.contenido or 0
                if circuito.circuito_etapa == Etapa.CONCPB and elemento.name in ["Pb", "Ag", "Zn"]:
                    past_resume.ley += circuito.ley_corregida or 0
                elif circuito.circuito_etapa == Etapa.CONCZN and elemento.name in ["Ag", "Zn"]:
                    past_resume.ley += circuito.ley_corregida or 0
                elif circuito.circuito_etapa == Etapa.CONCFE and elemento.name in ["Ag", "Au", "Fe"]:
                    past_resume.ley += circuito.ley_corregida or 0

        # Promediar por número de ensayes
        if ensayes:
            new_resume.recuperacion /= len(ensayes)
            new_resume.contenido /= len(ensayes)
            new_resume.ley /= len(ensayes)
        if past_ensayes:
            past_resume.recuperacion /= len(past_ensayes)
            past_resume.contenido /= len(past_ensayes)
            past_resume.ley /= len(past_ensayes)

        # Calcular comparativas en porcentaje
        def calcular_comparativa(actual, pasado):
            if pasado == 0:
                return 0
            return ((actual - pasado) / pasado) * 100

        new_resume.comparativa_recuperacion = calcular_comparativa(new_resume.recuperacion, past_resume.recuperacion)
        new_resume.comparativa_contenido = calcular_comparativa(new_resume.contenido, past_resume.contenido)
        new_resume.comparativa_ley = calcular_comparativa(new_resume.ley, past_resume.ley)

        resumen.append(new_resume)

    return resumen

def get_recuperaciones(init_date=None, final_date=None, elements=[], db=db_dependency):
    today = date.today()

    # Obtener el rango de fechas
    if init_date and final_date:
        try:
            init_date = date.fromisoformat(init_date)
            final_date = date.fromisoformat(final_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")
    else:
        # Si no hay fechas proporcionadas, usar últimos 30 días
        final_date = today
        init_date = today - timedelta(days=30)

    # Obtener los ensayes actuales
    ensayes = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= init_date,
        func.date(Ensaye.fecha) <= final_date
    ).all()

    if not ensayes:
        raise HTTPException(status_code=400, detail="No se encontraron ensayes en las fechas seleccionadas.")

    # Buscar solo los elementos solicitados (si hay)
    if elements:
        elementos = db.query(Elemento).filter(Elemento.id.in_(elements)).all()
    else:
        elementos = db.query(Elemento).all()

    if not elementos:
        raise HTTPException(status_code=400, detail="No se encontraron elementos con los IDs proporcionados.")

    ensayes_ids = [ensaye.id for ensaye in ensayes]
    etapas = ["CONCPB", "CONCZN", "CONCFE"]

    # Circuitos actuales (solo de los elementos buscados)
    circuitos = db.query(CircuitoElemento).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(ensayes_ids),
            CircuitoElemento.circuito_etapa.in_(etapas),
            CircuitoElemento.elemento_id.in_([e.id for e in elementos])  # Solo de los elementos buscados
        )
    ).all()

    if not circuitos:
        raise HTTPException(status_code=400, detail="No se encontraron circuitos para los elementos seleccionados.")

    recuperaciones = []

    for elemento in elementos:
        # Primero, mapeo: fecha -> set de ids de ensayes
        fecha_ensayes = {}

        for ensaye in ensayes:
            fecha = ensaye.fecha
            if fecha not in fecha_ensayes:
                fecha_ensayes[fecha] = set()
            fecha_ensayes[fecha].add(ensaye.id)

        # Después, acumulo la distribucion por fecha solo para el elemento actual
        fecha_valores = {}

        for circuito in circuitos:
            if elemento.id == circuito.elemento_id:
                ensaye_buscado = next((e for e in ensayes if e.id == circuito.circuito_ensaye_id), None)
                if not ensaye_buscado:
                    raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al intentar obtener la fecha de un ensaye.")
                
                fecha = ensaye_buscado.fecha

                if fecha not in fecha_valores:
                    fecha_valores[fecha] = 0

                fecha_valores[fecha] += circuito.distribucion or 0

        # Ahora construimos los valores finales (promedio por fecha)
        values = []

        for fecha, suma_distribucion in sorted(fecha_valores.items()):
            value = ElementoValorRecuperacion()
            value.date = fecha

            total_ensayes_en_fecha = len(fecha_ensayes.get(fecha, []))

            if total_ensayes_en_fecha > 0:
                value.valor = suma_distribucion / total_ensayes_en_fecha
            else:
                value.valor = 0

            values.append(value)

        # Creamos el objeto final para el elemento
        new_element = RecuperacionElemento()
        new_element.elemento = elemento.name
        new_element.valores = values

        recuperaciones.append(new_element)

    return recuperaciones
    
def get_contenidos(init_date=None, final_date=None, elements=[], db=db_dependency):
    today = date.today()

    # Obtener el rango de fechas
    if init_date and final_date:
        try:
            init_date = date.fromisoformat(init_date)
            final_date = date.fromisoformat(final_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")
    else:
        # Si no hay fechas proporcionadas, usar últimos 30 días
        final_date = today
        init_date = today - timedelta(days=30)

    # Obtener los ensayes actuales
    ensayes = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= init_date,
        func.date(Ensaye.fecha) <= final_date
    ).all()

    if not ensayes:
        raise HTTPException(status_code=400, detail="No se encontraron ensayes en las fechas seleccionadas.")

    # Buscar solo los elementos solicitados (si hay)
    if elements:
        elementos = db.query(Elemento).filter(Elemento.id.in_(elements)).all()
    else:
        elementos = db.query(Elemento).all()

    if not elementos:
        raise HTTPException(status_code=400, detail="No se encontraron elementos con los IDs proporcionados.")

    ensayes_ids = [ensaye.id for ensaye in ensayes]
    etapas = ["CONCPB", "CONCZN", "CONCFE"]

    # Circuitos actuales (solo de los elementos buscados)
    circuitos = db.query(CircuitoElemento).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(ensayes_ids),
            CircuitoElemento.circuito_etapa.in_(etapas),
            CircuitoElemento.elemento_id.in_([e.id for e in elementos])  # Solo de los elementos buscados
        )
    ).all()

    if not circuitos:
        raise HTTPException(status_code=400, detail="No se encontraron circuitos para los elementos seleccionados.")

    contenidos = []

    for elemento in elementos:
        # Primero, mapeo: fecha -> set de ids de ensayes
        fecha_ensayes = {}

        for ensaye in ensayes:
            fecha = ensaye.fecha
            if fecha not in fecha_ensayes:
                fecha_ensayes[fecha] = set()
            fecha_ensayes[fecha].add(ensaye.id)

        # Después, acumulo la distribucion por fecha solo para el elemento actual
        fecha_valores = {}

        for circuito in circuitos:
            if elemento.id == circuito.elemento_id:
                ensaye_buscado = next((e for e in ensayes if e.id == circuito.circuito_ensaye_id), None)
                if not ensaye_buscado:
                    raise HTTPException(status_code=500, detail="Ocurrió un error inesperado al intentar obtener la fecha de un ensaye.")
                
                fecha = ensaye_buscado.fecha

                if fecha not in fecha_valores:
                    fecha_valores[fecha] = 0

                fecha_valores[fecha] += circuito.contenido or 0

        # Ahora construimos los valores finales (promedio por fecha)
        values = []

        for fecha, suma_distribucion in sorted(fecha_valores.items()):
            value = ElementoValorContenido()
            value.date = fecha

            total_ensayes_en_fecha = len(fecha_ensayes.get(fecha, []))

            if total_ensayes_en_fecha > 0:
                value.valor = suma_distribucion / total_ensayes_en_fecha
            else:
                value.valor = 0

            values.append(value)

        # Creamos el objeto final para el elemento
        new_element = ContenidoElemento()
        new_element.elemento = elemento.name
        new_element.valores = values

        contenidos.append(new_element)

    return contenidos

def get_leyes(init_date=None, final_date=None, etapas=[], db=db_dependency):
    today = date.today()

    # Obtener el rango de fechas
    if init_date and final_date:
        try:
            init_date = date.fromisoformat(init_date)
            final_date = date.fromisoformat(final_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")
    else:
        # Si no hay fechas proporcionadas, usar últimos 30 días
        final_date = today
        init_date = today - timedelta(days=30)

    if not etapas:
        etapas = ["CONCPB", "CONCZN", "CONCFE"]
        
    # Obtener los ensayes actuales
    ensayes = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= init_date,
        func.date(Ensaye.fecha) <= final_date
    ).all()

    if not ensayes:
        raise HTTPException(status_code=400, detail="No se encontraron ensayes en las fechas seleccionadas.")

    elementos = db.query(Elemento).all()

    if not elementos:
        raise HTTPException(status_code=400, detail="No se encontraron elementos con los IDs proporcionados.")

    ensayes_ids = [ensaye.id for ensaye in ensayes]
    

    # Circuitos actuales (solo de los elementos buscados)
    circuitos = db.query(CircuitoElemento).filter(
        and_(
            CircuitoElemento.circuito_ensaye_id.in_(ensayes_ids),
            CircuitoElemento.circuito_etapa.in_(etapas),
            CircuitoElemento.elemento_id.in_([e.id for e in elementos])  # Solo de los elementos buscados
        )
    ).all()

    if not circuitos:
        raise HTTPException(status_code=400, detail="No se encontraron circuitos para los elementos seleccionados.")
    
    leyes = []

    for elemento in elementos:
        fecha_valores = {}

        for circuito in circuitos:
            # Solo procesar si el circuito es del elemento actual
            if circuito.elemento_id != elemento.id:
                continue

            ensaye_buscado = next((e for e in ensayes if e.id == circuito.circuito_ensaye_id), None)
            if not ensaye_buscado:
                continue

            fecha = ensaye_buscado.fecha

            # Determinar si la sección aplica según el elemento
            secciones_validas = []
            if elemento.name == "Ag":
                secciones_validas = [Etapa.CONCPB, Etapa.CONCZN]
            elif elemento.name == "Zn":
                secciones_validas = [Etapa.CONCPB, Etapa.CONCZN]
            elif elemento.name == "Pb":
                secciones_validas = [Etapa.CONCPB]
            elif elemento.name in ["Au", "Fe"]:
                secciones_validas = [Etapa.CONCFE]

            if circuito.circuito_etapa not in secciones_validas:
                continue

            if fecha not in fecha_valores:
                fecha_valores[fecha] = {} # Cambiamos la lista por un diccionario para almacenar valores por sección

            seccion = circuito.circuito_etapa
            valor = circuito.ley_corregida or 0

            if seccion not in fecha_valores[fecha]:
                fecha_valores[fecha][seccion] = [] # Inicializamos una lista para los valores de esta sección

            fecha_valores[fecha][seccion].append(valor)

        # Ya que tenemos todos los valores de este elemento, ahora formamos la respuesta con el promedio
        valores = []
        for fecha, valores_por_seccion in fecha_valores.items():
            for seccion, lista_de_valores in valores_por_seccion.items():
                promedio = sum(lista_de_valores) / len(lista_de_valores) if lista_de_valores else 0
                valores.append({
                    "date": fecha,
                    "seccion": seccion,
                    "valor": promedio
                })

        leyes.append({
            "elemento": elemento.name,
            "valores": valores
        })
    return leyes

def get_ensayes(init_date=None, final_date=None, user_id=None, skip=0, limit=10, db=db_dependency):
    today = date.today()

    # Obtener el rango de fechas
    if init_date and final_date:
        try:
            init_date = date.fromisoformat(init_date)
            final_date = date.fromisoformat(final_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")
    else:
        # Si no hay fechas proporcionadas, usar últimos 30 días
        final_date = today
        init_date = today - timedelta(days=30)
        
    query = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= init_date,
        func.date(Ensaye.fecha) <= final_date
    )

    # Filtrar por user_id si se proporciona
    if user_id is not None:
        query = query.filter(Ensaye.user_id == user_id)

    ensayes = query.offset(skip * limit).limit(limit).all()

    return [EnsayeResponse.model_validate(ensaye) for ensaye in ensayes]

def get_ensayes_dia(db=db_dependency):
    today = date.today()
    
    query = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
    ).filter(
        func.date(Ensaye.fecha) >= today,
        func.date(Ensaye.fecha) <= today
    )
    
    ensayes = query.all()

    return ensayes

def _fetch_dashboard_part_safely(fetch_function, *args, **kwargs):
    """
    Ejecuta una función para obtener una parte del dashboard.
    Si la función lanza HTTPException, devuelve el mensaje de detalle.
    Si lanza cualquier otra Exception, devuelve un mensaje de error genérico para esa parte.
    Si tiene éxito, devuelve los datos.
    """
    function_name = fetch_function.__name__
    try:
        return fetch_function(*args, **kwargs)
    except HTTPException as he:
        # Para errores "esperados" (como "no hay datos"), devolvemos el mensaje.
        print(f"INFO: Faltan datos para '{function_name}' en dashboard principal: {he.detail}")
        return {
                "isError": True,
                "detail": he.detail
            }  # Esto se convertirá en el valor para la clave de esta sección
    except Exception as e:
        # Para errores de servidor inesperados dentro de la función de servicio.
        print(f"ERROR: Error inesperado en '{function_name}' al construir dashboard principal: {type(e).__name__} - {e}")
        return f"Error interno al procesar datos para '{function_name.replace('get_', '')}'."
