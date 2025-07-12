import os
import logging
import hmac
import hashlib
import base64
import json
import time
import uuid
import requests
from google.cloud import firestore
from dotenv import load_dotenv

# Загрузка .env переменных
load_dotenv()

# Инициализация Firestore
db = firestore.Client()

# Ключи из .env
API_KEY = os.getenv("BLOFIN_API_KEY")
API_SECRET = os.getenv("BLOFIN_API_SECRET")
API_PASSPHRASE = os.getenv("BLOFIN_API_PASSPHRASE")

if not all([API_KEY, API_SECRET, API_PASSPHRASE]):
    logging.error("❌ Не заданы переменные окружения для BloFin API")

# 🔐 Подпись запроса
def create_signature(path: str, method: str, timestamp: str, nonce: str, body: dict | None = None) -> str:
    if body:
        body_str = json.dumps(body, separators=(',', ':'))
        prehash = f"{path}{method}{timestamp}{nonce}{body_str}"
    else:
        prehash = f"{path}{method}{timestamp}{nonce}"

    logging.info(f"[BLOFIN] Prehash string: {prehash}")
    hex_digest = hmac.new(API_SECRET.encode(), prehash.encode(), hashlib.sha256).hexdigest()
    signature = base64.b64encode(hex_digest.encode()).decode()
    logging.info(f"[BLOFIN] Signature (Base64): {signature}")
    return signature

# 🔍 Проверка UID и KYC
def find_uid_info(target_uid: str, limit: int = 30, max_pages: int = 50) -> dict | None:
    base_path = "/api/v1/affiliate/invitees"
    method = "GET"

    for page in range(1, max_pages + 1):
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        query = f"?limit={limit}&page={page}"
        full_path = f"{base_path}{query}"

        signature = create_signature(full_path, method, timestamp, nonce)

        headers = {
            "ACCESS-KEY": API_KEY,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-NONCE": nonce,
            "ACCESS-PASSPHRASE": API_PASSPHRASE,
            "Content-Type": "application/json"
        }

        url = f"https://openapi.blofin.com{full_path}"
        logging.info(f"[BLOFIN] 🔄 Партия {page}, запрос к {url}")

        try:
            response = requests.get(url, headers=headers)
            logging.info(f"[BLOFIN] Статус ответа: {response.status_code}")
            data = response.json()
            logging.info(f"[BLOFIN] Ответ: {data}")
        except Exception:
            logging.exception("[BLOFIN] ❌ Ошибка запроса")
            break

        if data.get("code") not in ("0", "200"):
            logging.warning(f"[BLOFIN] ⚠️ Ошибка API: {data.get('msg')}")
            break

        invitees = data.get("data", [])
        for invitee in invitees:
            if str(invitee.get("uid")) == str(target_uid):
                logging.info(f"[BLOFIN] ✅ UID найден: {target_uid}")
                return invitee  # Возвращаем весь объект

        if len(invitees) < limit:
            logging.info("[BLOFIN] 🔚 Конец списка — UID не найден")
            break

    logging.warning(f"[BLOFIN] ❌ UID {target_uid} не найден")
    return None

# 🔗 Привязка UID к Telegram ID
def link_blofin_uid(telegram_id: str, blofin_uid: str) -> dict:
    logging.info(f"[BLOFIN] Привязка UID {blofin_uid} к Telegram ID {telegram_id}")

    uid_info = find_uid_info(blofin_uid)
    if not uid_info:
        logging.warning(f"[BLOFIN] Ошибка проверки UID: UID not found")
        return {"status": "error", "message": "ERROR_NOT_FOUND"}

    try:
        users_ref = db.collection("telegram_users")

        # Проверка, не занят ли UID другим пользователем
        query = users_ref.where("blofin_uid", "==", str(blofin_uid)).limit(1).stream()
        existing_users = list(query)

        if existing_users:
            existing_doc = existing_users[0]
            logging.warning(f"[BLOFIN] UID {blofin_uid} уже привязан к Telegram ID {existing_doc.id}")
            if existing_doc.id != telegram_id:
                return {"status": "error", "message": "ERROR_TAKEN"}
            else:
                logging.info(f"[BLOFIN] UID {blofin_uid} уже был привязан к этому пользователю.")
                return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}

        user_ref = users_ref.document(telegram_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logging.error(f"[BLOFIN] ❌ Пользователь с telegram_id {telegram_id} не найден в базе.")
            return {"status": "error", "message": "ERROR_UNKNOWN"}

        update_data = {
            "blofin_uid": str(blofin_uid)
        }

        kyc_level = int(uid_info.get("kycLevel", 0))
        if kyc_level > 0:
            logging.info(f"[BLOFIN] ✅ У UID {blofin_uid} есть KYC")
            update_data["blofin_kyc"] = "KYC"
        else:
            logging.info(f"[BLOFIN] ⛔ У UID {blofin_uid} нет KYC")

        user_ref.update(update_data)
        logging.info(f"[BLOFIN] ✅ Привязка успешна")
        return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}

    except Exception:
        logging.exception("[BLOFIN] ❌ Firestore ошибка")
        return {"status": "error", "message": "Firestore error"}
