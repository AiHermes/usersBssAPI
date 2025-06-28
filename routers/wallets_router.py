from fastapi import APIRouter, Body, HTTPException
import logging

# Импортируем нашу основную сервисную функцию
from services.wallet_service import create_new_wallet_for_user

router = APIRouter()

@router.post("/create_wallet")
async def create_wallet_endpoint(payload: dict = Body(...)):
    """
    Эндпоинт для создания нового BNB кошелька для пользователя.
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Параметр 'user_id' обязателен.")
    
    # --- ЛОГИРОВАНИЕ ---
    logging.info(f"[ROUTER] Получен запрос на создание кошелька для user_id: {user_id}")
    logging.info(f"[ROUTER] Вызываю wallet_service.create_new_wallet_for_user...")
    
    # Вызываем нашу сервисную функцию
    result = create_new_wallet_for_user(user_id)
    
    if result and result.get("status") == "success":
        address = result.get("address")
        # --- ЛОГИРОВАНИЕ ---
        logging.info(f"[ROUTER] Сервис успешно отработал. Адрес: {address}. Отправляю ответ 200 OK.")
        return {
            "status": "success",
            "user_id": user_id,
            "bnb_wallet_address": address
        }
    else:
        # --- ЛОГИРОВАНИЕ ---
        logging.error(f"[ROUTER] Сервис вернул ошибку для user_id: {user_id}. Отправляю ответ 500.")
        raise HTTPException(
            status_code=500, 
            detail="Произошла внутренняя ошибка при создании кошелька. Проверьте логи сервера."
        )