# services/wallet_service.py
import logging
from web3 import Account
from config import get_db_client
# --- 1. ИСПРАВЛЯЕМ ИМПОРТ ---
# Импортируем правильную функцию для сохранения ключа
from services.security_service import store_private_key 
# Импортируем функцию для сигнала в Remote Config
from services.remote_config_service import signal_update as remote_config_signal

def create_new_wallet_for_user(user_id: str) -> dict | None:
    """
    Создает новый кошелек, если он еще не существует.
    """
    db = get_db_client()
    if not db:
        logging.error("[WALLET_SERVICE] Не удалось получить клиент БД.")
        return None

    try:
        logging.info(f"[WALLET_SERVICE] Запрос на создание/получение кошелька для user_id: {user_id}")
        user_doc_ref = db.collection("telegram_users").document(user_id)
        
        user_doc = user_doc_ref.get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            existing_address = user_data.get("bnb_wallet_address")
            if existing_address:
                logging.info(f"✅ [WALLET_SERVICE] Кошелек для user_id: {user_id} уже существует. Создание пропускается.")
                return {"address": existing_address, "status": "exists"}
        else:
            logging.warning(f"[WALLET_SERVICE] Документ для user_id: {user_id} не найден.")
            return None

        logging.info(f"[WALLET_SERVICE] Кошелек не найден, начинаю процесс создания...")
        
        account = Account.create()
        address = account.address
        private_key = account.key.hex()
        
        # --- 2. ИСПОЛЬЗУЕМ ПРАВИЛЬНОЕ НАЗВАНИЕ ФУНКЦИИ ---
        secret_name = store_private_key(user_id, private_key)
        
        if not secret_name:
            logging.error(f"[WALLET_SERVICE] security_service не смог сохранить ключ для {user_id}.")
            return None

        batch = db.batch()
        batch.update(user_doc_ref, {"bnb_wallet_address": address})
        secure_wallet_doc_ref = db.collection("secure_wallets").document(user_id)
        batch.set(secure_wallet_doc_ref, {"address": address, "secret_name": secret_name})
        batch.commit()
        
        logging.info(f"✅ [WALLET_SERVICE] Новый кошелек для user_id: {user_id} создан.")
        
        # Вызываем сигнал в Remote Config
        remote_config_signal()
        
        return {"address": address, "status": "success"}

    except Exception as e:
        logging.exception(f"❌ [WALLET_SERVICE] КРИТИЧЕСКАЯ ОШИБКА для user_id: {user_id}: {e}")
        return None