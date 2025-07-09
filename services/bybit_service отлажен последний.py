import os
import time
import hmac
import hashlib
import logging
import requests
import json
from dotenv import load_dotenv
from config import get_db_client # Импортируем наш клиент для работы с базой данных

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- Конфигурация Bybit API ---
API_KEY = os.getenv("BYBIT_API_KEY")
SECRET_KEY = os.getenv("BYBIT_SECRET_KEY")
BASE_URL = "https://api.bybit.com"

def _get_bybit_signature(timestamp: str, api_key: str, recv_window: str, secret_key: str, params: str = "") -> str:
    """Генерирует подпись для запроса Bybit API v5."""
    message = timestamp + api_key + recv_window + params
    return hmac.new(bytes(secret_key, "utf-8"), bytes(message, "utf-8"), hashlib.sha256).hexdigest()

def _is_user_direct_referral(uid: str) -> bool:
    """
    Вспомогательная функция для проверки, является ли UID прямым рефералом.
    """
    if not all([API_KEY, SECRET_KEY]):
        logging.error("[BYBIT] API ключи не настроены в .env")
        return False
    
    try:
        request_path = "/v5/affiliate/aff-user-list"
        cursor = ""
        while True:
            timestamp = str(int(time.time() * 1000))
            recv_window = "10000"
            params_dict = {"size": 50, "cursor": cursor}
            params_str = "&".join([f"{k}={v}" for k, v in sorted(params_dict.items())])
            signature = _get_bybit_signature(timestamp, API_KEY, recv_window, SECRET_KEY, params_str)
            headers = {'X-BAPI-API-KEY': API_KEY, 'X-BAPI-SIGN': signature, 'X-BAPI-TIMESTAMP': timestamp, 'X-BAPI-RECV-WINDOW': recv_window, 'Content-Type': 'application/json'}
            full_url = BASE_URL + request_path + "?" + params_str
            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") == 0:
                result = data.get("result", {})
                referral_list = result.get("list", [])
                for referral in referral_list:
                    if referral.get("userId") == uid:
                        return True
                cursor = result.get("nextPageCursor", "")
                if not cursor:
                    return False
            else:
                return False
    except Exception as e:
        logging.exception(f"❌ [BYBIT] Критическая ошибка при проверке реферала: {e}")
        return False

def link_bybit_uid(telegram_id: str, bybit_uid: str) -> dict:
    """
    Основная функция: проверяет UID и привязывает его к пользователю Telegram.
    """
    # --- Шаг 1: Проверка, является ли UID нашим рефералом ---
    logging.info(f"[BYBIT_LINK] Начинаю проверку UID: {bybit_uid}")
    if not _is_user_direct_referral(bybit_uid):
        logging.warning(f"[BYBIT_LINK] Отказ: UID {bybit_uid} не является прямым рефералом.")
        return {"status": "error", "message": "UID нет в нашей реферальной системе"}

    logging.info(f"[BYBIT_LINK] Успех: UID {bybit_uid} является рефералом.")

    try:
        db = get_db_client()
        users_ref = db.collection('telegram_users')

        # --- Шаг 2: Проверка, не занят ли этот UID другим пользователем ---
        logging.info(f"[BYBIT_LINK] Проверяю, не занят ли UID {bybit_uid} в базе данных...")
        query = users_ref.where('bybit_uid', '==', bybit_uid).limit(1).stream()
        
        # Преобразуем генератор в список, чтобы проверить, есть ли в нем элементы
        existing_users = list(query)
        
        if existing_users:
            # Проверяем, не принадлежит ли найденный UID самому этому пользователю
            if existing_users[0].id == telegram_id:
                 logging.info(f"[BYBIT_LINK] UID {bybit_uid} уже привязан к этому пользователю {telegram_id}.")
                 return {"status": "success", "message": f"Этот UID уже привязан к вашему аккаунту."}
            
            logging.warning(f"[BYBIT_LINK] Отказ: UID {bybit_uid} уже принадлежит другому пользователю.")
            return {"status": "error", "message": "Ошибка. UID принадлежит другому пользователю"}

        logging.info(f"[BYBIT_LINK] Успех: UID {bybit_uid} свободен.")

        # --- Шаг 3: UID свободен, привязываем его к текущему пользователю ---
        user_doc_ref = users_ref.document(telegram_id)
        
        # Проверяем, существует ли пользователь
        if not user_doc_ref.get().exists:
            logging.error(f"[BYBIT_LINK] Ошибка: Пользователь с telegram_id {telegram_id} не найден в базе.")
            return {"status": "error", "message": "Пользователь не найден"}
            
        user_doc_ref.update({'bybit_uid': bybit_uid})
        logging.info(f"[BYBIT_LINK] Успех: UID {bybit_uid} успешно привязан к пользователю {telegram_id}.")
        
        return {"status": "success", "message": f"Успех. UID добавлен к пользователю {telegram_id}"}

    except Exception as e:
        logging.exception(f"❌ [BYBIT_LINK] Критическая ошибка при работе с базой данных: {e}")
        return {"status": "error", "message": "Внутренняя ошибка сервера"}