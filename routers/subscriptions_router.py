# Файл: routers/subscriptions_router.py
from fastapi import APIRouter, Body, HTTPException
from services.subscription_service import purchase_subscription

router = APIRouter()

@router.post("/buy_subscription")
async def buy_subscription_endpoint(payload: dict = Body(...)):
    """
    Эндпоинт для покупки подписки.
    Ожидает: { "telegram_id": "...", "shop_id": "..." }
    """
    telegram_id = payload.get("telegram_id")
    shop_id = payload.get("shop_id")

    if not telegram_id or not shop_id:
        raise HTTPException(status_code=400, detail="Необходимо указать telegram_id и shop_id.")

    result = purchase_subscription(telegram_id, shop_id)

    if result.get("status") == "success":
        return result
    else:
        # Возвращаем ошибку с сообщением от сервиса
        raise HTTPException(status_code=402, detail=result.get("message", "Произошла ошибка"))