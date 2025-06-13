from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import joinedload, Session
from sqlalchemy import func, and_
from starlette import status
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional
import asyncio

from db.database import db_dependency
from auth.auth import permission_required
from models.Ensaye import Ensaye, TipoEnsayes
from models.Usuario import User
from models.weaks.Producto import Producto
from models.weaks.Circuito import Circuito
from models.associations.elemento_circuito import CircuitoElemento
from schemas.usuario_schema import UsuarioBase
from schemas.ensaye_schema import CreateEnsayeRequest, EnsayeResponse, ElementoResponse, CircuitoElementoResponse, CircuitoResponse, ProductoResponse
from calculo.calculo import ejecutar_calculo_lagrange
from sockets.connection_manager import manager

router = APIRouter(
    prefix="/ensaye",
    tags=['ensaye']
)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_ensaye(
    db: db_dependency,
    ensaye_request: CreateEnsayeRequest,
    permission: dict = Depends(permission_required("Ensayista"))
    ):
    try:
        user_id = permission.id

        if isinstance(ensaye_request.fecha, datetime):
            ensaye_fecha = ensaye_request.fecha.date()
        else:
            ensaye_fecha = ensaye_request.fecha

        start_of_day = datetime.combine(ensaye_fecha, time.min)  # 00:00:00
        end_of_day = datetime.combine(ensaye_fecha, time.max)    # 23:59:59.999999

        existing_ensaye = db.query(Ensaye).filter(
            Ensaye.fecha >= start_of_day,
            Ensaye.fecha <= end_of_day,
            Ensaye.turno == ensaye_request.turno
        ).first()

        if existing_ensaye:
            raise HTTPException(
                status_code=400,
                detail=f"El ensaye del turno {ensaye_request.turno} ya ha sido registrado para la fecha {ensaye_fecha}."
            )

        # Crear Ensaye
        db_ensaye = Ensaye(
            fecha=ensaye_request.fecha,
            turno=ensaye_request.turno,
            tipo_ensaye=ensaye_request.tipo_ensaye,
            user_id=user_id
        )
        db.add(db_ensaye)
        db.flush()  # Genera el ID sin commit definitivo

        # Crear Producto
        db_producto = Producto(
            ensaye_id=db_ensaye.id,
            molienda_humeda=ensaye_request.molienda_humeda,
            humedad=ensaye_request.humedad,
            cabeza_general=ensaye_request.cabeza_general
        )
        db.add(db_producto)

        # Crear Circuitos y sus elementos
        for circuito in ensaye_request.circuitos:
            # Crear Circuito
            db_circuito = Circuito(
                ensaye_id=db_ensaye.id,
                etapa=circuito.etapa
            )
            db.add(db_circuito)

            # Crear asociaciones con Elementos
            for elemento in circuito.elementos:
                db_association = CircuitoElemento(
                    circuito_ensaye_id=db_ensaye.id,
                    circuito_etapa=circuito.etapa,
                    elemento_id=elemento.elemento_id,
                    existencia_teorica=elemento.existencia_teorica,
                    desviacion_estandar=elemento.desviacion_estandar,
                    contenido=elemento.contenido,
                    ley_corregida=elemento.ley_corregida,
                    distribucion=elemento.distribucion
                )
                db.add(db_association)

        db.commit()
        db.refresh(db_ensaye)
        
         # Obtener usuarios ANTES de agendar la tarea, si los necesitas como están en este momento.
        # Cuidado si son objetos SQLAlchemy y ProcessPoolExecutor, podrían no ser picklables o estar detached.
        # Es mejor pasar IDs o datos simples si es posible.
        usuarios_para_notificacion = db.query(User).all() # Asumo User es tu modelo SQLAlchemy

        # Agendar la tarea en segundo plano
        asyncio.create_task(
            ejecutar_calculo_lagrange(
                users=usuarios_para_notificacion, # Pasa la lista de usuarios
                essay_id=db_ensaye.id,
                essay_date=db_ensaye.fecha.date(), # Asegúrate que sea un objeto date
                essay_shift=db_ensaye.turno,
                circuitos=ensaye_request # Pasa el request original o las partes necesarias
            )
        )

        # Esta es tu primera "respuesta": Ensaye almacenado.
        return {"message": "Ensaye registrado. El procesamiento continuará en segundo plano.", "ensaye_id": db_ensaye.id}

    except HTTPException as http_exc:
        db.rollback() # Es buena práctica si la excepción no es por validación previa
        raise http_exc
    except Exception as e:
        db.rollback()
        # Loguea el error real para depuración
        print(f"Error inesperado al crear ensaye: {e}") # logging.error(f"...", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al procesar el ensaye: {str(e)}")


    
@router.get("/")
async def get_all_ensayes(
    db: db_dependency, 
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta", "Supervisor de Ensayista")),
    skip: int = Query(0, description="Número de página (0 por defecto)"),
    limit: int = Query(5, le=50, description="Cantidad de registros por página (máx. 50)"),
    init_date: Optional[str] = Query(None, description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, description="Fecha final de busqueda (opcional)"),
    shift: Optional[int] = Query(None, alias="shift", description="Filtro de turno de reporte (opcional)"),
    laboratory: Optional[TipoEnsayes] = Query(None, alias="laboratory", description="Filtro de laboratorio (opcional)"),
    ):
    try:
        
        # Validar que si viene init_date, también venga final_date y viceversa
        if (init_date or final_date):
            if (init_date and not final_date) or (final_date and not init_date):
                raise HTTPException(
                    status_code=422,
                    detail="Debe proporcionar ambas fechas (inicio y fin) o ninguna"
                )
        MX_TIMEZONE = ZoneInfo("America/Mexico_City")
        today = datetime.now(MX_TIMEZONE).date()
    
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
            
            
            
        query = db.query(Ensaye).options(
            joinedload(Ensaye.user),
            joinedload(Ensaye.producto),
            joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
        )
        
         # Agregar filtros opcionales
        if shift:
            query = query.filter(Ensaye.turno == shift)

        if laboratory:
            query = query.filter(Ensaye.laboratorio == laboratory)
            
        # Agregar filtro por rango de fechas
        if init_date and final_date:
            # Asegúrate que la columna se llame 'fecha' en tu modelo Ensaye
            query = query.filter(Ensaye.fecha.between(init_date, final_date))
                
        # Obtener el conteo total (antes de paginar)
        total_count = query.count()
            
        # Aplicar paginación
        ensayes = query.offset(skip * limit).limit(limit).all()

        # Convertir a modelos de respuesta
        data = [EnsayeResponse.model_validate(ensaye) for ensaye in ensayes]
            
        return {
            "data": data,
            "totalCount": total_count,
            "page": skip,
            "pageSize": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
@router.get("/ensayista")
async def get_ensayes_by_ensayista(
    db: db_dependency,
    permission: dict = Depends(permission_required("Ensayista")),
    skip: int = Query(0, description="Número de página (0 por defecto)"),
    limit: int = Query(2, le=50, description="Cantidad de registros por página (máx. 50)"),
    init_date: Optional[str] = Query(None, description="Fecha inicial de busqueda (opcional)"),
    final_date: Optional[str] = Query(None, description="Fecha final de busqueda (opcional)"),
    shift: Optional[int] = Query(None, alias="shift", description="Filtro de turno de reporte (opcional)"),
    laboratory: Optional[TipoEnsayes] = Query(None, alias="laboratory", description="Filtro de laboratorio (opcional)"),
    ):
        try:
            
             # Validar que si viene init_date, también venga final_date y viceversa
            if (init_date and not final_date) or (final_date and not init_date):
                raise HTTPException(
                    status_code=422,
                    detail="Debe proporcionar ambas fechas (inicio y fin) o ninguna"
                )
        
            user_id = permission.id
            
            MX_TIMEZONE = ZoneInfo("America/Mexico_City")
            today = datetime.now(MX_TIMEZONE).date()

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
            ).filter(Ensaye.user_id == user_id).filter(
                func.date(Ensaye.fecha) >= init_date,
                func.date(Ensaye.fecha) <= final_date
            )
            # Agregar filtros opcionales
            if shift:
                query = query.filter(Ensaye.turno == shift)

            if laboratory:
                query = query.filter(Ensaye.laboratorio == laboratory)
                
           # Obtener el conteo total (antes de paginar)
            total_count = query.count()
            
            # Aplicar paginación
            ensayes = query.offset(skip * limit).limit(limit).all()
            
            print(query)
            # Convertir a modelos de respuesta
            data = [EnsayeResponse.model_validate(ensaye) for ensaye in ensayes]
            
            return {
                "data": data,
                "totalCount": total_count,
                "page": skip,
                "pageSize": limit
            }
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))  
        
@router.get("/ensayista/{id}", response_model=EnsayeResponse)
async def get_ensayes_by_ensayista_by_id(
    db: db_dependency,
    id: int,
    permission: dict = Depends(permission_required("Ensayista")),
    skip: int = Query(0, alias="page", description="Número de página (0 por defecto)"),
    limit: int = Query(5, le=50, description="Cantidad de registros por página (máx. 50)")
    ):
        try:
            user_id = permission.id
            
            ensaye = db.query(Ensaye).options(
                joinedload(Ensaye.user),
                joinedload(Ensaye.producto),
                joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
            ).offset(skip * limit).limit(limit).filter(Ensaye.user_id == user_id, Ensaye.id == id).first()
            
            return EnsayeResponse.model_validate(ensaye)
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) 
        
@router.get("/{id}", response_model=EnsayeResponse)
async def get_ensaye_by_id(
    db: db_dependency,
    id: int,
    permission: dict = Depends(permission_required("Supervisor General", "Supervisor de Planta", "Supervisor de Ensayista"))
):
    try:
        ensaye = db.query(Ensaye).options(
            joinedload(Ensaye.user),
            joinedload(Ensaye.producto),
            joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
        ).filter(Ensaye.id == id).first()

        if not ensaye:
            raise HTTPException(status_code=404, detail="Ensaye no encontrado")

        # --- INICIO DE LA LÓGICA DE ORDENAMIENTO ---

        # 1. Define el orden exacto que deseas para las etapas.
        #    Añadí "Colas Pb" y "Colas Zn" al final por si aparecen.
        order_list = [
            "Cabeza Flotacion",
            "Concentrado Pb",
            "Concentrado Zn",
            "Concentrado Fe",
            "Colas Finales",
            "Colas Pb",
            "Colas Zn"
        ]
        
        # 2. Crea un mapa para que cada etapa tenga un valor numérico de orden.
        #    Etapas no listadas recibirán un valor alto (99) para ir al final.
        order_map = {etapa: i for i, etapa in enumerate(order_list)}

        # 3. Ordena la lista de circuitos del ensaye usando el mapa como clave.
        ensaye.circuitos.sort(key=lambda circuito: order_map.get(circuito.etapa, 99))

        # --- FIN DE LA LÓGICA DE ORDENAMIENTO ---
        
        # Ahora el objeto 'ensaye' tiene sus circuitos ordenados antes de validarlo.
        return EnsayeResponse.model_validate(ensaye)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@router.websocket("/ws/status/{ensaye_id}")
async def websocket_ensaye_status(websocket: WebSocket, ensaye_id: str):
    """
    Endpoint WebSocket para recibir actualizaciones de estado de un ensaye.
    El cliente debe conectarse a este endpoint después de crear un ensaye.
    """
    await manager.connect(ensaye_id, websocket)
    try:
        while True:
            # Esta implementación es principalmente para que el servidor envíe datos.
            # Podrías querer manejar pings del cliente para mantener viva la conexión.
            # O si el cliente envía datos, procesarlos aquí.
            data = await websocket.receive_text() # Espera un mensaje (ej. ping)
            # print(f"WS PING received for {ensaye_id}: {data}")
            # await websocket.send_text(f"Pong: {data}") # Opcional: responder a pings
            pass # Simplemente mantener la conexión abierta
    except WebSocketDisconnect:
        print(f"WebSocket active connection closed by client for ensaye_id: {ensaye_id}")
    except Exception as e:
        print(f"Unexpected error in WebSocket for ensaye_id {ensaye_id}: {e}")
    finally:
        manager.disconnect(ensaye_id, websocket)
        

