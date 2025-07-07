from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
import logging
from datetime import datetime, timedelta, timezone

# ИЗМЕНЕНО: Импортируем функцию для получения клиента БД
from config import get_db_client 

# Создаем новый роутер
router = APIRouter()

# Модель для входящих данных
class CheckinPayload(BaseModel):
    telegram_id: str

# --- API ЭНДПОИНТ ДЛЯ ЧЕКИНА ---
@router.post("/check-in")
async def perform_checkin(payload: CheckinPayload):
    """
    Выполняет операцию "чекина" для пользователя.
    """
    # ИЗМЕНЕНО: Получаем клиент БД с помощью функции
    db = get_db_client()
    if not db:
        raise HTTPException(status_code=500, detail="Firestore client not initialized")

    user_id = payload.telegram_id
    logging.info(f"▶️  Получен запрос на чекин для пользователя: {user_id}")

    try:
        # 1. Получаем документ пользователя из Firestore
        user_ref = db.collection('telegram_users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logging.error(f"❌ Пользователь с ID {user_id} не найден.")
            raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")

        user_data = user_doc.to_dict()
        
        # 2. Вычисляем текущий "тающий" баланс
        base_balance = user_data.get('balance_usdt', 0.0)
        checkin_date = user_data.get('checkin_date')
        
        now = datetime.now(timezone.utc)
        available_balance = base_balance

        if checkin_date and now < checkin_date:
            seconds_left = (checkin_date - now).total_seconds()
            if seconds_left > 0:
                decay_amount = seconds_left * 0.000024
                available_balance = base_balance - decay_amount
        
        available_balance = max(0, available_balance)
        logging.info(f"💰 Текущий доступный баланс для {user_id}: {available_balance}")

        # 3. Выполняем операции чекина
        new_balance = available_balance + 2.0736
        new_checkin_date = now + timedelta(hours=24)
        
        # 4. Обновляем документ пользователя в Firestore
        user_ref.update({
            'balance_usdt': new_balance,
            'checkin_date': new_checkin_date
        })
        
        logging.info(f"✅ Чекин для {user_id} выполнен. Новый баланс: {new_balance:.6f}")

        return {
            "status": "success",
            "message": "Check-in successful.",
            "new_balance": new_balance,
            "new_checkin_date": new_checkin_date.isoformat()
        }

    except Exception as e:
        logging.exception(f"❌ Ошибка во время чекина для пользователя {user_id}:")
        raise HTTPException(status_code=500, detail=str(e))