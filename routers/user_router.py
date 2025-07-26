# routers/user_router.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.user_service import create_initial_user_record

router = APIRouter()

# Модель для данных, которые мы ожидаем в запросе
class UserCreateRequest(BaseModel):
    telegram_id: str

@router.post("/users/create")
async def create_user_endpoint(request: UserCreateRequest):
    """
    Эндпоинт для создания начальной записи пользователя.
    Ожидает в теле запроса: { "telegram_id": "ВАШ_ID" }
    """
    if not request.telegram_id:
        raise HTTPException(status_code=400, detail="Необходимо указать telegram_id.")
    
    result = create_initial_user_record(telegram_id=request.telegram_id)
    
    # Если сервис вернул ошибку, передаем ее клиенту
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    
    # Возвращаем успешный ответ (даже если пользователь уже существует, это не ошибка)
    return result