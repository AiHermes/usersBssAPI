import logging
from web3 import Account

# Импортируем наши собственные модули
from config import db
from services.security_service import store_private_key
# ОШИБОЧНАЯ СТРОКА БЫЛА ЗДЕСЬ И ТЕПЕРЬ УДАЛЕНА

def create_new_wallet_for_user(user_id: str) -> dict | None:
    """
    Создает новый кошелек, сохраняет приватный ключ и обновляет Firestore.
    """
    try:
        logging.info(f"[WALLET_SERVICE] Старт создания кошелька для user_id: {user_id}")
        
        account = Account.create()
        address = account.address
        private_key = account.key.hex()
        
        logging.info(f"[WALLET_SERVICE] Сгенерирован адрес: {address}")

        secret_name = store_private_key(user_id, private_key)
        
        if not secret_name:
            logging.error(f"[WALLET_SERVICE] security_service не смог сохранить ключ для {user_id}. Прерываю.")
            return None

        logging.info(f"[WALLET_SERVICE] Ключ сохранен. Начинаю запись в Firestore batch для user_id: {user_id}...")
        
        batch = db.batch()
        
        user_doc_ref = db.collection("telegram_users").document(user_id)
        batch.update(user_doc_ref, {"bnb_wallet_address": address})
        
        secure_wallet_doc_ref = db.collection("secure_wallets").document(user_id)
        batch.set(secure_wallet_doc_ref, {"address": address, "secret_name": secret_name})
        
        batch.commit()
        
        logging.info(f"✅ [WALLET_SERVICE] Кошелек для user_id: {user_id} успешно создан и записан в DB.")
        
        return {"address": address, "status": "success"}

    except Exception as e:
        logging.exception(f"❌ [WALLET_SERVICE] КРИТИЧЕСКАЯ ОШИБКА для user_id: {user_id}: {e}")
        return None