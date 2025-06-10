from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.orm import joinedload
from sqlalchemy import func, and_
from datetime import date, timedelta
from typing import List, Optional

from db.database import db_dependency
from auth.auth import permission_required

from models.Ensaye import Ensaye, TipoEnsayes
from models.Elemento import Elemento
from models.weaks.Circuito import Circuito
from models.associations.elemento_circuito import CircuitoElemento, Etapa

from schemas.reporte_schema import DataReporte 


router = APIRouter(
    prefix="/reporte",
    tags=['reporte']
)

@router.get("/")
async def get_reporte(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta", "Supervisor de Ensayista")),
    init_date: Optional[str] = Query(None, alias="initial date", description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, alias="final date", description="Fecha final de busqueda (opcional)"),
    shift: Optional[int] = Query(None, alias="shift", description="Filtro de turno de reporte (opcional)"),
    laboratory: Optional[TipoEnsayes] = Query(None, alias="laboratory", description="Filtro de laboratorio (opcional)"),
    user: Optional[int] = Query(None, alias="user", description="Filtro de usuario (opcional)"),
    elements: Optional[List[int]] = Query(None, description="Lista de elementos para filtrar (opcional)")
):
    try:
        report = _fetch_report_part_safely(get_report, init_date=init_date, final_date=final_date, shift=shift, laboratory=laboratory, user=user, elements=elements, db=db)
        
        return {
            "reporte": report
        }
        
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

def get_report(
    init_date: Optional[str] = None,
    final_date: Optional[str] = None,
    shift: Optional[str] = None,
    laboratory: Optional[str] = None,
    user: Optional[int] = None,
    elements: Optional[List[int]] = Query(None),
    db=db_dependency
):
        
    today = date.today()

    # Obtener el rango de fechas
    if init_date and final_date:
        try:
            init_date = date.fromisoformat(init_date)
            final_date = date.fromisoformat(final_date)
        except Exception:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")
    else:
        final_date = today
        init_date = today - timedelta(days=30)

    # Construir la consulta base
    query = db.query(Ensaye).options(
        joinedload(Ensaye.user),
        joinedload(Ensaye.producto),
        joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
    ).filter(
        func.date(Ensaye.fecha) >= init_date,
        func.date(Ensaye.fecha) <= final_date
    )

    # Agregar filtros opcionales
    if shift:
        query = query.filter(Ensaye.turno == shift)

    if laboratory:
        if laboratory == "Laboratorio Real":
            query = query.filter(Ensaye.tipo_ensaye == "REAL")
        else:
            query = query.filter(Ensaye.tipo_ensaye == "CONCILIADO")

    if user:
        query = query.filter(Ensaye.user_id == user)

    ensayes = query.all()
    
    if not ensayes:
        raise HTTPException(status_code=404, detail="No se encontraron ensayes con los filtros seleccionados.")
    
     # Buscar solo los elementos solicitados (si hay)
    if elements:
        elementos = db.query(Elemento).filter(Elemento.id.in_(elements)).all()
    else:
        elementos = db.query(Elemento).all()

    if not elementos:
        raise HTTPException(status_code=404, detail="No se encontraron elementos con los IDs proporcionados.")

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

    recuperations = get_recuperation_report(ensayes=ensayes, elementos=elementos, circuitos=circuitos)
    contents = get_contents_report(ensayes=ensayes, elementos=elementos, circuitos=circuitos)
    laws = get_laws_report(ensayes=ensayes, elementos=elementos, circuitos=circuitos)
    return {
        "recuperaciones": recuperations,
        "contenidos": contents,
        "leyes": laws
    }

def get_recuperation_report(ensayes = [], elementos = [], circuitos = []):
    # Inicializar acumuladores por elemento
    elemento_recuperacion_total = {elemento.id: 0 for elemento in elementos}

    # Contar el total de ensayes
    total_ensayes = len(ensayes)

    # Acumular la recuperación por elemento
    for ensaye in ensayes:
        for elemento in elementos:
            recuperacion = sum(
                circuito.distribucion or 0
                for circuito in circuitos
                if circuito.elemento_id == elemento.id and circuito.circuito_ensaye_id == ensaye.id
            )
            elemento_recuperacion_total[elemento.id] += recuperacion

    # Calcular el promedio
    promedios = []
    for elemento in elementos:
        new_element = DataReporte()
        new_element.elemento = elemento.name
        new_element.valor = round(elemento_recuperacion_total[elemento.id] / total_ensayes, 2)
        promedios.append(new_element)

    return promedios

def get_contents_report(ensayes = [], elementos = [], circuitos = []):
    # Inicializar acumuladores por elemento
    elemento_contenido_total = {elemento.id: 0 for elemento in elementos}

    # Contar el total de ensayes
    total_ensayes = len(ensayes)

    # Acumular la recuperación por elemento
    for ensaye in ensayes:
        for elemento in elementos:
            content = sum(
                circuito.contenido or 0
                for circuito in circuitos
                if circuito.elemento_id == elemento.id and circuito.circuito_ensaye_id == ensaye.id
            )
            elemento_contenido_total[elemento.id] += content

    # Calcular el promedio
    promedios = []
    for elemento in elementos:
        new_element = DataReporte()
        new_element.elemento = elemento.name
        new_element.valor= round(elemento_contenido_total[elemento.id] / total_ensayes, 2)
        promedios.append(new_element)

    return promedios

def get_laws_report(ensayes=[], elementos=[], circuitos=[]):
    etapaCONCPB = []
    etapaCONCZN = []
    etapaCONCFE = []

    total_ensayes = len(ensayes) if ensayes else 1  # evitar división por cero

    for ensaye in ensayes:
        for elemento in elementos:
            for circuito in circuitos:
                if circuito.circuito_ensaye_id != ensaye.id:
                    continue

                # Verificamos que el circuito corresponda al elemento actual
                if circuito.elemento_id != elemento.id:
                    continue

                secciones_validas = []

                if elemento.name in ["Ag", "Zn"]:
                    secciones_validas.extend([Etapa.CONCPB, Etapa.CONCZN])
                if elemento.name == "Pb":
                    secciones_validas.append(Etapa.CONCPB)
                if elemento.name in ["Au", "Fe", "Ag"]:
                    secciones_validas.append(Etapa.CONCFE)

                if not secciones_validas:
                    continue

                etapa = circuito.circuito_etapa
                if etapa not in secciones_validas:
                    continue

                if etapa == Etapa.CONCPB:
                    etapa_lista = etapaCONCPB
                elif etapa == Etapa.CONCZN:
                    etapa_lista = etapaCONCZN
                elif etapa == Etapa.CONCFE:
                    etapa_lista = etapaCONCFE
                else:
                    continue

                # Buscar si ya existe un DataReporte para ese elemento
                reporte_existente = next((r for r in etapa_lista if r.elemento == elemento.name), None)

                if reporte_existente:
                    reporte_existente.valor += circuito.ley_corregida or 0
                else:
                    new_element = DataReporte()
                    new_element.elemento = elemento.name
                    new_element.valor = circuito.ley_corregida or 0
                    etapa_lista.append(new_element)

    # Promediar entre el total de ensayes
    for etapa_lista in [etapaCONCPB, etapaCONCZN, etapaCONCFE]:
        for reporte in etapa_lista:
            reporte.valor = round(reporte.valor / total_ensayes, 4)

    return {
        "etapas": [
            {"etapa": "CONCPB", "valores": etapaCONCPB},
            {"etapa": "CONCZN", "valores": etapaCONCZN},
            {"etapa": "CONCFE", "valores": etapaCONCFE}
        ]
    }
    
def _fetch_report_part_safely(fetch_function, *args, **kwargs):
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
        return he # Esto se convertirá en el valor para la clave de esta sección
    except Exception as e:
        # Para errores de servidor inesperados dentro de la función de servicio.
        print(f"ERROR: Error inesperado en '{function_name}' al construir dashboard principal: {type(e).__name__} - {e}")
        return f"Error interno al procesar datos para '{function_name.replace('get_', '')}'."