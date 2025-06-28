from fastapi import APIRouter, Body, HTTPException
import logging
from services.wallet_service import create_new_wallet_for_user

router = APIRouter()

@router.post("/create_wallet")
async def create_wallet_endpoint(payload: dict = Body(...)):
    """
    Создает новый BNB кошелек для пользователя, если он еще не существует.
    """
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="Параметр 'user_id' обязателен.")
    
    logging.info(f"[ROUTER] Получен запрос на создание кошелька для user_id: {user_id}")
    
    result = create_new_wallet_for_user(user_id)
    
    # --- ОБНОВЛЕННЫЙ БЛОК ОБРАБОТКИ ОТВЕТА ---
    if result:
        status = result.get("status")
        address = result.get("address")

        if status == "success":
            logging.info(f"[ROUTER] Сервис создал новый кошелек. Адрес: {address}. Отправляю ответ 200 OK.")
            return {
                "status": "success",
                "user_id": user_id,
                "bnb_wallet_address": address,
                "message": "New wallet has been created successfully."
            }
        elif status == "exists":
            logging.info(f"[ROUTER] Сервис нашел существующий кошелек. Адрес: {address}. Отправляю ответ 200 OK.")
            return {
                "status": "exists",
                "user_id": user_id,
                "bnb_wallet_address": address,
                "message": "Wallet for this user already exists."
            }
    
    # Сюда мы попадем, если сервис вернул None (ошибка)
    logging.error(f"[ROUTER] Сервис вернул ошибку для user_id: {user_id}. Отправляю ответ 500.")
    raise HTTPException(
        status_code=500, 
        detail="Произошла внутренняя ошибка при создании кошелька. Проверьте логи сервера."
    )