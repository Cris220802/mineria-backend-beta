from fastapi import APIRouter, Depends, HTTPException, Query


router = APIRouter(
    prefix="/predicciones",
    tags=['predicciones']
)

@router.post("/")
async def predict(
    
):
    return