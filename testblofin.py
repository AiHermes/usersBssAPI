import os
import logging
import hmac
import hashlib
import base64
import uuid
import json
import time
import requests
from google.cloud import firestore
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Firestore клиент
db = firestore.Client()

# Получение ключей из .env
BLOFIN_API_KEY = os.getenv("BLOFIN_API_KEY")
BLOFIN_API_SECRET = os.getenv("BLOFIN_API_SECRET")
BLOFIN_API_PASSPHRASE = os.getenv("BLOFIN_API_PASSPHRASE")

if not all([BLOFIN_API_KEY, BLOFIN_API_SECRET, BLOFIN_API_PASSPHRASE]):
    logging.error("❌ Один или несколько ключей BloFin отсутствуют в .env")


def create_signature(path: str, method: str, timestamp: str, nonce: str, body: dict = None) -> str:
    """
    Генерация подписи для BloFin API.
    """
    if body:
        body_str = json.dumps(body, separators=(',', ':'))
        prehash = f"{path}{method}{timestamp}{nonce}{body_str}"
    else:
        prehash = f"{path}{method}{timestamp}{nonce}"

    logging.info(f"[BLOFIN] Prehash string: {prehash}")

    hex_digest = hmac.new(BLOFIN_API_SECRET.encode(), prehash.encode(), hashlib.sha256).hexdigest()
    signature = base64.b64encode(hex_digest.encode()).decode()

    logging.info(f"[BLOFIN] Signature (Base64): {signature}")
    return signature


def check_blofin_uid(uid_to_find: str, max_pages: int = 100) -> dict:
    """
    Поиск UID среди прямых рефералов с пагинацией.
    """
    path = "/api/v1/affiliate/invitees"
    method = "GET"
    page = 1
    found = False
    before = None

    for attempt in range(max_pages):
        timestamp = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        signature = create_signature(path, method, timestamp, nonce)

        headers = {
            "ACCESS-KEY": BLOFIN_API_KEY,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-NONCE": nonce,
            "ACCESS-PASSPHRASE": BLOFIN_API_PASSPHRASE,
            "Content-Type": "application/json"
        }

        query_params = {
            "limit": "30",
        }
        if before:
            query_params["before"] = before

        url = f"https://openapi.blofin.com{path}"
        logging.info(f"[BLOFIN] 🔄 Партия {page}, запрос к {url} с query: {query_params}")

        try:
            response = requests.get(url, headers=headers, params=query_params)
            logging.info(f"[BLOFIN] Статус ответа: {response.status_code}")
            data = response.json()
            logging.info(f"[BLOFIN] Ответ: {data}")
        except Exception as e:
            logging.exception("[BLOFIN] ❌ Ошибка при отправке запроса или чтении ответа")
            return {"status": "error", "error": "Request failed"}

        if data.get("code") != 200:
            return {"status": "error", "error": data.get("msg", "API Error")}

        invitees = data.get("data", [])
        if not invitees:
            break

        for user in invitees:
            if str(user.get("uid")) == str(uid_to_find):
                found = True
                return {"status": "success", "uid": uid_to_find, "data": user}

        # для следующей страницы
        before = str(invitees[-1].get("id"))
        page += 1

    return {"status": "error", "error": "UID not found"}


def link_blofin_uid(telegram_id: str, blofin_uid: str) -> dict:
    """
    Привязка BloFin UID к Telegram ID.
    """
    logging.info(f"[BLOFIN] Привязка UID {blofin_uid} к Telegram ID {telegram_id}")

    result = check_blofin_uid(blofin_uid)
    if result["status"] == "error":
        logging.warning(f"[BLOFIN] Ошибка проверки UID: {result['error']}")
        return {"status": "error", "message": result["error"]}

    try:
        doc_ref = db.collection("telegram_users").document(telegram_id)
        doc_ref.set({"blofin_uid": blofin_uid}, merge=True)
        logging.info("[BLOFIN] ✅ UID успешно сохранён в Firestore")

        return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}
    except Exception as e:
        logging.exception("[BLOFIN] ❌ Ошибка при сохранении UID в Firestore")
        return {"status": "error", "message": "Firestore error"}
