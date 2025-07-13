import os
import time
import hmac
import logging
import requests
from hashlib import sha256
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"

# 🔐 Генерация подписи и строки параметров
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
    except Exception as e:
        logging.exception("❌ Ошибка при обработке JSON-ответа BingX")
        return {"code": -1, "msg": "INVALID_JSON", "data": {}}

# 🔍 Проверка — является ли UID нашим рефералом
def is_uid_my_referral(uid: str) -> dict:
    page = 1
    while True:
        result = get_referrals_page(page_index=page)

        if result.get("code") != 0:
            logging.warning("❌ Ошибка BingX API: %s", result)
            return {"status": "error", "message": "API_ERROR"}

        data = result.get("data", {})
        referrals = data.get("list", [])

        if not isinstance(referrals, list):
            logging.error("❌ Неверный формат данных: 'list' не является списком")
            return {"status": "error", "message": "INVALID_DATA", "raw": result}

        for ref in referrals:
            if isinstance(ref, dict) and str(ref.get("uid")) == str(uid):
                logging.info(f"✅ Найден реферал: {uid}")
                return {"status": "success", "uid": uid}

        if len(referrals) < 50:
            break
        page += 1

    logging.info(f"❌ UID {uid} не найден среди рефералов")
    return {"status": "error", "message": "ERROR_NOT_FOUND"}
