from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import joinedload
from starlette import status
from typing import List
import asyncio

from db.database import db_dependency
from auth.auth import permission_required
from models.Ensaye import Ensaye
from models.Usuario import User
from models.weaks.Producto import Producto
from models.weaks.Circuito import Circuito
from models.associations.elemento_circuito import CircuitoElemento
from schemas.usuario_schema import UsuarioBase
from schemas.ensaye_schema import CreateEnsayeRequest, EnsayeResponse, ElementoResponse, CircuitoElementoResponse, CircuitoResponse, ProductoResponse
from auth.auth import permission_required
from calculo.calculo import ejecutar_calculo_lagrange

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
                    existencia_teorica_corregida=elemento.existencia_teorica_corregida,
                    distribucion=elemento.distribucion
                )
                db.add(db_association)

        db.commit()
        
        usuarios = db.query(User).all()
        
        # Iniciar el cálculo en segundo plano
        asyncio.create_task(ejecutar_calculo_lagrange(users = usuarios, essay_date=db_ensaye.fecha, essay_id=db_ensaye.id, essay_shift=db_ensaye.turno, circuitos=ensaye_request))
        
        return {"message": "Ensaye registrado exitosamente", "ensaye_id": db_ensaye.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/", response_model=List[EnsayeResponse])
async def get_all_ensayes(db: db_dependency, permission: dict = Depends(permission_required("Supervisor General"))):
    try:
        ensayes = db.query(Ensaye).options(
            joinedload(Ensaye.user),
            joinedload(Ensaye.producto),
            joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
        ).all()
        return [EnsayeResponse.model_validate(ensaye) for ensaye in ensayes]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
@router.get("/ensayista", response_model=List[EnsayeResponse])
async def get_ensayes_by_ensayista(
    db: db_dependency,
    permission: dict = Depends(permission_required("Ensayista"))
    ):
        try:
            user_id = permission.id
            ensayes = db.query(Ensaye).options(
                joinedload(Ensaye.user),
                joinedload(Ensaye.producto),
                joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
            ).filter(Ensaye.user_id == user_id).all()
            
            return [EnsayeResponse.model_validate(ensaye) for ensaye in ensayes]
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))  
        
@router.get("/ensayista/{id}", response_model=EnsayeResponse)
async def get_ensayes_by_ensayista_by_id(
    db: db_dependency,
    id: int,
    permission: dict = Depends(permission_required("Ensayista"))
    ):
        try:
            user_id = permission.id
            
            ensaye = db.query(Ensaye).options(
                joinedload(Ensaye.user),
                joinedload(Ensaye.producto),
                joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
            ).filter(Ensaye.user_id == user_id, Ensaye.id == id).first()
            
            return EnsayeResponse.model_validate(ensaye)
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) 
        
@router.get("/{id}", response_model=EnsayeResponse)
async def get_ensaye_by_id(
    db: db_dependency,
    id: int,
    permission: dict = Depends(permission_required("Supervisor General"))):
        try:
            ensaye = db.query(Ensaye).options(
                joinedload(Ensaye.user),
                joinedload(Ensaye.producto),
                joinedload(Ensaye.circuitos).joinedload(Circuito.elementos).joinedload(CircuitoElemento.elemento)
            ).filter(Ensaye.id == id).first()
            
            if not ensaye:
                raise HTTPException(status_code=404, detail="Ensaye no encontrado")
            
            return EnsayeResponse.model_validate(ensaye)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
