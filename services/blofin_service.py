import os
import logging
import hmac
import hashlib
import base64
import json
import time
import uuid
import requests
from datetime import datetime, timedelta, timezone
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

BONUS_IMAGE_URL = "https://firebasestorage.googleapis.com/v0/b/bss2025-b1285.firebasestorage.app/o/pictures%2Fallert%2FBloFinAiHermesPro.png?alt=media&token=05541c0d-ddf4-4a01-8398-f361c73d87d2"

if not all([API_KEY, API_SECRET, API_PASSPHRASE]):
    logging.error("❌ Не заданы переменные окружения для BloFin API")

def create_signature(path: str, method: str, timestamp: str, nonce: str, body: dict | None = None) -> str:
    body_str = json.dumps(body, separators=(',', ':')) if body else ''
    prehash = f"{path}{method}{timestamp}{nonce}{body_str}"
    hex_digest = hmac.new(API_SECRET.encode(), prehash.encode(), hashlib.sha256).hexdigest()
    return base64.b64encode(hex_digest.encode()).decode()

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
        try:
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
        except Exception:
            logging.exception("[BLOFIN] ❌ Ошибка запроса")
            break
        if data.get("code") not in ("0", "200"):
            break
        for invitee in data.get("data", []):
            if str(invitee.get("uid")) == str(target_uid):
                return invitee
        if len(data.get("data", [])) < limit:
            break
    return None

def link_blofin_uid(telegram_id: str, blofin_uid: str) -> dict:
    logging.info(f"[BLOFIN] Привязка UID {blofin_uid} к Telegram ID {telegram_id}")
    uid_info = find_uid_info(blofin_uid)
    if not uid_info:
        return {"status": "error", "message": "ERROR_NOT_FOUND"}

    try:
        now = datetime.now(timezone.utc)
        users_ref = db.collection("telegram_users")
        user_ref = users_ref.document(telegram_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            logging.error("[BLOFIN] ❌ Пользователь не найден")
            return {"status": "error", "message": "ERROR_UNKNOWN"}

        # Проверка, не занят ли UID другим пользователем
        query = users_ref.where("blofin_uid", "==", str(blofin_uid)).limit(1).stream()
        for doc in query:
            if doc.id != telegram_id:
                logging.warning(f"[BLOFIN] UID {blofin_uid} уже использован другим пользователем: {doc.id}")
                user_ref.update({"blofin_uid": str(blofin_uid)})
                _write_alerts_and_messages(user_ref, telegram_id,
                    "⚠️ UID BloFin использован ранее. 🎁 Бонус в 4 дня не предоставляется.")
                return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}

        # Обновляем UID и KYC
        update_data = {"blofin_uid": str(blofin_uid)}
        if int(uid_info.get("kycLevel", 0)) > 0:
            update_data["blofin_kyc"] = "KYC"
        user_ref.update(update_data)

        # Проверка blofin4days
        if user_doc.to_dict().get("blofin4days", False):
            logging.info("[BLOFIN] ⚠️ Бонус уже был начислен ранее")
            _write_alerts_and_messages(user_ref, telegram_id,
                "🎉 Новый UID BloFin успешно привязан. 🎁 Бонус в 4 дня уже был начислен ранее — повторное начисление не предусмотрено")
            return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}

        # Проверка, был ли UID использован ранее
        users_all = users_ref.stream()
        for other_user in users_all:
            if other_user.id == telegram_id:
                continue
            history_ref = other_user.reference.collection("subscriptionHistory")
            bonus_found = list(history_ref
                .where("shopID", "==", "4blofinAihermesPro")
                .where("blofinuid", "==", str(blofin_uid)).limit(1).stream())
            if bonus_found:
                logging.warning(f"[BLOFIN] UID {blofin_uid} использован ранее другим")
                user_ref.update({"blofin_uid": str(blofin_uid)})
                _write_alerts_and_messages(user_ref, telegram_id,
                    "⚠️ UID BloFin использован ранее. 🎁 Бонус в 4 дня не предоставляется.")
                return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}

        # Продление подписки
        subs_ref = user_ref.collection("subscriptions")
        target_sub = None
        for doc in subs_ref.stream():
            data = doc.to_dict()
            if data.get("subscription_type") == "AIHermesPRO":
                target_sub = doc
                break

        end_date = now + timedelta(days=4)
        if target_sub:
            sub_data = target_sub.to_dict()
            old_end = sub_data.get("end_date")
            if isinstance(old_end, datetime) and old_end > now:
                end_date = old_end + timedelta(days=4)
            subs_ref.document(target_sub.id).update({
                "end_date": end_date
            })
            logging.info(f"[BLOFIN] 🕒 Подписка продлена до {end_date}")
        else:
            subs_ref.document().set({
                "subscription_type": "AIHermesPRO",
                "end_date": end_date,
                "tvEndData": False  # Проставим явно False, чтобы формат соответствовал скриншоту
            })
            logging.info(f"[BLOFIN] 🆕 Создана новая подписка до {end_date}")

        # История
        user_ref.collection("subscriptionHistory").add({
            "name": "4 дня Blofin AIHermesPro",
            "price": 0,
            "purchaseDate": now,
            "shopID": "4blofinAihermesPro",
            "blofinuid": str(blofin_uid)
        })
        logging.info("[BLOFIN] 🧾 Запись в subscriptionHistory")

        # Alerts + Messages
        _write_alerts_and_messages(user_ref, telegram_id,
            "🎉 Спасибо за регистрацию на бирже BloFin! 🎁 Вам начислены 4 дня подписки на AIHermesPro!")

        # Обновление флага
        user_ref.update({"blofin4days": True})

        return {"status": "success", "telegram_id": telegram_id, "uid": blofin_uid}

    except Exception:
        logging.exception("[BLOFIN] ❌ Ошибка при начислении бонуса")
        return {"status": "error", "message": "Firestore error"}

def _write_alerts_and_messages(user_ref, telegram_id, message_text):
    now = datetime.now(timezone.utc)
    user_ref.collection("alerts").add({
        "message": message_text,
        "read": False,
        "timestamp": now,
        "type": 1
    })
    logging.info(f"[BLOFIN] 🔔 Добавлено уведомление: {message_text}")

    db.collection("messages").add({
        "bot_name": "bssbot",
        "created_at": now,
        "memo": {"text": message_text},
        "image_url": BONUS_IMAGE_URL,
        "status": "pending",
        "telegram_id": telegram_id
    })
    logging.info(f"[BLOFIN] 💬 Создано сообщение для Telegram")
