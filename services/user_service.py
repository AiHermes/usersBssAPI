import logging
from datetime import datetime, timezone
from config import get_db_client
from firebase_admin import firestore

def create_initial_user_record(telegram_id: str) -> dict:
    """
    Создает начальную запись пользователя в Firestore со всеми полями.
    """
    db = get_db_client()
    if not db:
        return {"status": "error", "message": "Database connection failed."}

    user_ref = db.collection('telegram_users').document(telegram_id)

    try:
        if user_ref.get().exists:
            logging.warning(f"[USER_SERVICE] Пользователь с ID {telegram_id} уже существует.")
            return {"status": "exists", "message": "User already exists."}

        # --- Значения по умолчанию, как на скриншоте ---
        now = datetime.now(timezone.utc)
        default_data = {
            # Основные данные
            "id": telegram_id,
            "first_name": "",
            "last_name": "",
            "username": "",
            "language_code": "",
            "photo_url": "",
            "created_at": now,
            
            # Финансовые данные
            "balance_usdt": 0.0,
            "bnb_wallet_address": "",
            "ton_wallet_address": "",
            
            # Данные по биржам
            "bybit_uid": "",
            "bybit_kyc": False,
            "bybit14days": False, # Предполагаю, что это тоже булево поле
            "blofin_uid": "",
            "blofin4days": False,
            "blofin10days": False,
            "bingx_uid": "",
            "bingx_kyc": False,
            "bingx4days": False,
            "bingx14days": False,

            # Прочие системные поля
            "allows_write_to_pm": False, # Устанавливаем в False по умолчанию
            "checkin_date": now,
            "tradingview": ""
        }

        user_ref.set(default_data)
        logging.info(f"✅ [USER_SERVICE] Успешно создан новый пользователь с ID: {telegram_id}")
        
        return {"status": "success", "message": "User created successfully."}

    except Exception as e:
        logging.exception(f"❌ [USER_SERVICE] Ошибка при создании пользователя {telegram_id}: {e}")
        return {"status": "error", "message": str(e)}