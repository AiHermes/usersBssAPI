import os
import time
import hmac
import hashlib
import logging
import requests
import json
from dotenv import load_dotenv
from config import get_db_client

# Загружаем переменные окружения из .env файла
load_dotenv()

API_KEY = os.getenv("BYBIT_API_KEY")
SECRET_KEY = os.getenv("BYBIT_SECRET_KEY")
BASE_URL = "https://api.bybit.com"


def _get_bybit_signature(timestamp: str, api_key: str, recv_window: str, secret_key: str, params: str = "") -> str:
    message = timestamp + api_key + recv_window + params
    return hmac.new(bytes(secret_key, "utf-8"), bytes(message, "utf-8"), hashlib.sha256).hexdigest()


def _is_user_direct_referral(uid: str) -> bool:
    if not all([API_KEY, SECRET_KEY]):
        logging.error("[BYBIT] API ключи не настроены в .env")
        return False

    try:
        request_path = "/v5/affiliate/aff-user-list"
        cursor = ""

        while True:
            timestamp = str(int(time.time() * 1000))
            recv_window = "10000"

            params_dict = {
                "size": 50,
                "cursor": cursor
            }
            params_str = "&".join([f"{k}={v}" for k, v in sorted(params_dict.items())])
            signature = _get_bybit_signature(timestamp, API_KEY, recv_window, SECRET_KEY, params_str)

            headers = {
                'X-BAPI-API-KEY': API_KEY,
                'X-BAPI-SIGN': signature,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': recv_window,
                'Content-Type': 'application/json'
            }

            full_url = BASE_URL + request_path + "?" + params_str
            logging.info(f"[BYBIT] Запрос страницы с курсором: '{cursor}'")

            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("retCode") == 0:
                result = data.get("result", {})
                referral_list = result.get("list", [])

                for referral in referral_list:
                    if referral.get("userId") == uid:
                        logging.info(f"[BYBIT] ✅ Пользователь {uid} НАЙДЕН.")
                        return True

                cursor = result.get("nextPageCursor", "")
                if not cursor:
                    logging.info(f"[BYBIT] Все страницы проверены. Пользователь {uid} не найден.")
                    return False
            else:
                logging.error(f"[BYBIT] API вернул ошибку: {data.get('retMsg')}")
                return False

    except Exception as e:
        logging.exception(f"❌ [BYBIT] Критическая ошибка при проверке реферала: {e}")
        return False


def link_bybit_uid(telegram_id: str, bybit_uid: str) -> dict:
    """
    Основная функция: проверяет UID и привязывает его к пользователю Telegram.
    """
    logging.info(f"[BYBIT_LINK] Начинаю проверку UID: {bybit_uid}")
    if not _is_user_direct_referral(bybit_uid):
        logging.warning(f"[BYBIT_LINK] Отказ: UID {bybit_uid} не является прямым рефералом.")
        return {"status": "error", "message": "ERROR_NOT_FOUND"}

    logging.info(f"[BYBIT_LINK] Успех: UID {bybit_uid} является рефералом.")

    try:
        db = get_db_client()
        users_ref = db.collection('telegram_users')

        logging.info(f"[BYBIT_LINK] Проверяю, не занят ли UID {bybit_uid} в базе данных...")
        query = users_ref.where('bybit_uid', '==', bybit_uid).limit(1).stream()
        existing_users = list(query)

        if existing_users:
            if existing_users[0].id == telegram_id:
                logging.info(f"[BYBIT_LINK] UID {bybit_uid} уже привязан к этому пользователю {telegram_id}.")
                return {"status": "success", "message": "SUCCESS"}

            logging.warning(f"[BYBIT_LINK] Отказ: UID {bybit_uid} уже принадлежит другому пользователю.")
            return {"status": "error", "message": "ERROR_TAKEN"}

        logging.info(f"[BYBIT_LINK] Успех: UID {bybit_uid} свободен.")

        user_doc_ref = users_ref.document(telegram_id)
        if not user_doc_ref.get().exists:
            logging.error(f"[BYBIT_LINK] Ошибка: Пользователь с telegram_id {telegram_id} не найден в базе.")
            return {"status": "error", "message": "ERROR_UNKNOWN"}

        # Получаем KYC-статус
        kyc_result = get_referral_kyc_status(bybit_uid)
        if kyc_result.get("status") == "success":
            bybit_kyc_status = kyc_result.get("kyc_status", "UNKNOWN")
        else:
            bybit_kyc_status = "UNKNOWN"

        # Обновляем Firestore
        user_doc_ref.update({
            'bybit_uid': bybit_uid,
            'bybit_kyc': bybit_kyc_status
        })

        logging.info(f"[BYBIT_LINK] Успех: UID {bybit_uid} успешно привязан к пользователю {telegram_id}.")
        return {"status": "success", "message": "SUCCESS"}

    except Exception as e:
        logging.exception(f"❌ [BYBIT_LINK] Критическая ошибка при работе с базой данных: {e}")
        return {"status": "error", "message": "ERROR_UNKNOWN"}



def get_referral_kyc_status(uid: str) -> dict:
    """
    Проверяет, прошёл ли пользователь KYC. Возвращает 'KYC' или 'No KYC'.
    """
    if not all([API_KEY, SECRET_KEY]):
        logging.error("[BYBIT] API ключи не настроены.")
        return {"status": "error", "message": "API_KEYS_NOT_SET"}

    try:
        request_path = "/v5/affiliate/aff-user-list"
        cursor = ""

        while True:
            timestamp = str(int(time.time() * 1000))
            recv_window = "10000"

            params_dict = {
                "size": 50,
                "cursor": cursor
            }
            params_str = "&".join([f"{k}={v}" for k, v in sorted(params_dict.items())])
            signature = _get_bybit_signature(timestamp, API_KEY, recv_window, SECRET_KEY, params_str)

            headers = {
                'X-BAPI-API-KEY': API_KEY,
                'X-BAPI-SIGN': signature,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': recv_window,
                'Content-Type': 'application/json'
            }

            url = BASE_URL + request_path + "?" + params_str
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            logging.info(f"[BYBIT][KYC] Ответ от Bybit: {json.dumps(data, indent=2)}")

            if data.get("retCode") != 0:
                logging.warning(f"[BYBIT][KYC] Ошибка в ответе API: {data.get('retMsg')}")
                return {"status": "error", "message": "BYBIT_API_ERROR"}

            for ref in data.get("result", {}).get("list", []):
                if ref.get("userId") == uid:
                    is_kyc = ref.get("isKyc", False)
                    kyc_status = "KYC" if is_kyc else "No KYC"
                    logging.info(f"[BYBIT][KYC] Найден {uid}, статус KYC: {kyc_status}")
                    return {"status": "success", "kyc_status": kyc_status}

            cursor = data.get("result", {}).get("nextPageCursor", "")
            if not cursor:
                break

        logging.info(f"[BYBIT][KYC] UID {uid} не найден среди твоих рефералов.")
        return {"status": "error", "message": "USER_NOT_FOUND"}

    except Exception as e:
        logging.exception(f"[BYBIT][KYC] Ошибка при проверке KYC: {e}")
        return {"status": "error", "message": "INTERNAL_ERROR"}