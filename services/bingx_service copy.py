import os
import time
import hmac
import logging
import requests
from hashlib import sha256
from dotenv import load_dotenv
from config import get_db_client

# Загрузка переменных окружения
load_dotenv()

API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"

# 🔐 Генерация подписи
def generate_signature(params_map: dict) -> tuple[str, str]:
    sorted_keys = sorted(params_map)
    params_str = "&".join([f"{key}={params_map[key]}" for key in sorted_keys])
    signature = hmac.new(SECRET_KEY.encode(), params_str.encode(), digestmod=sha256).hexdigest()
    logging.info(f"🔐 Signature: {signature}")
    return signature, params_str

# 📄 Получение страницы рефералов
def get_referrals_page(page_index: int = 1, page_size: int = 50):
    timestamp = str(int(time.time() * 1000))
    params_map = {
        "pageIndex": str(page_index),
        "pageSize": str(page_size),
        "timestamp": timestamp
    }
    signature, params_str = generate_signature(params_map)
    url = f"{BASE_URL}/openApi/agent/v1/account/inviteAccountList?{params_str}&signature={signature}"
    headers = {"X-BX-APIKEY": API_KEY}

    logging.info(f"📄 BingX API Запрос: {url}")
    response = requests.get(url, headers=headers)
    try:
        return response.json()
    except Exception:
        logging.exception("❌ Ошибка при обработке JSON-ответа BingX")
        return {"code": -1, "msg": "INVALID_JSON", "data": {}}

# ✅ Проверка — является ли UID нашим рефералом
def find_uid_info(uid: str) -> dict:
    page = 1
    while True:
        result = get_referrals_page(page_index=page)

        if result.get("code") != 0:
            logging.warning("❌ Ошибка BingX API: %s", result)
            return {"found": False}

        data = result.get("data", {})
        referrals = data.get("list", [])

        if not isinstance(referrals, list):
            logging.error("❌ Неверный формат данных: 'list' не является списком")
            return {"found": False}

        for ref in referrals:
            if isinstance(ref, dict) and str(ref.get("uid")) == str(uid):
                logging.info(f"✅ Найден реферал: {uid}")
                logging.info(f"📦 Полный JSON по UID {uid}: {ref}")
                return {
                    "found": True,
                    "kyc": ref.get("kycResult", False)
                }

        if len(referrals) < 50:
            break
        page += 1

    logging.info(f"❌ UID {uid} не найден среди рефералов")
    return {"found": False}

# 🔗 Привязка UID к Telegram ID
def link_bingx_uid(telegram_id: str, uid: str) -> dict:
    logging.info(f"[BINGX] ▶️ Запрос /link-uid | Telegram ID: {telegram_id} | UID: {uid}")

    db = get_db_client()
    if not db:
        return {"status": "error", "message": "DATABASE_ERROR"}

    # 1. Проверка через BingX
    ref_info = find_uid_info(uid)
    if not ref_info["found"]:
        return {"status": "error", "message": "ERROR_NOT_FOUND"}

    # 2. Проверка — UID не занят другим пользователем
    users_ref = db.collection("telegram_users")
    conflicting = users_ref.where("bingx_uid", "==", uid).stream()
    conflicting_users = [doc.id for doc in conflicting]

    if conflicting_users and telegram_id not in conflicting_users:
        return {"status": "error", "message": "ERROR_TAKEN"}

    # 3. Запись UID (и при необходимости KYC) в Firestore
    try:
        user_doc = users_ref.document(telegram_id)
        update_data = {"bingx_uid": uid}

        # Проверка KYC по полю kycResult
        raw_kyc = ref_info.get("kyc", False)
        logging.info(f"🔍 Получен kycResult из BingX: {raw_kyc} (тип: {type(raw_kyc)})")

        if isinstance(raw_kyc, bool) and raw_kyc is True:
            update_data["bingx_kyc"] = "KYC"
            logging.info(f"📌 Добавляем bingx_kyc='KYC'")
        else:
            logging.info(f"ℹ️ Не добавляем bingx_kyc: kycResult={raw_kyc}")

        user_doc.set(update_data, merge=True)
        return {"status": "success", "message": f"UID {uid} привязан к пользователю {telegram_id}"}
    except Exception:
        logging.exception("❌ Ошибка при записи в Firestore")
        return {"status": "error", "message": "FIRESTORE_WRITE_ERROR"}
