from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
# Импортируем только ту функцию, которая нам нужна
from services.bybit_service import link_bybit_uid

router = APIRouter()

class BybitLinkRequest(BaseModel):
    telegram_id: str
    bybit_uid: str

@router.post("/link-uid")
async def link_bybit_uid_endpoint(request: BybitLinkRequest):
    """
    Эндпоинт для проверки и привязки Bybit UID к пользователю Telegram.
    """
    print(f"[DEBUG] Получено тело запроса: {request.dict()}")
    if not request.telegram_id or not request.bybit_uid:
        raise HTTPException(status_code=400, detail="Необходимо указать telegram_id и bybit_uid.")
    
    result = link_bybit_uid(telegram_id=request.telegram_id, bybit_uid=request.bybit_uid)
    
    if result["status"] == "error":
        raise HTTPException(status_code=409, detail=result["message"])
        
    return result