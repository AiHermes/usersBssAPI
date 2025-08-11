 #bingx_service.py
import os
import time
import hmac
import logging
import requests
from hashlib import sha256
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from config import get_db_client

load_dotenv()

API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"

BONUS_IMAGE_URL = "https://firebasestorage.googleapis.com/v0/b/bss2025-b1285.firebasestorage.app/o/pictures%2Fallert%2FBingXAiHermesPro.png?alt=media&token=1b0fbd89-fc48-4c53-9303-2859d12d35d2"

def generate_signature(params_map: dict) -> tuple[str, str]:
    sorted_keys = sorted(params_map)
    params_str = "&".join([f"{key}={params_map[key]}" for key in sorted_keys])
    signature = hmac.new(SECRET_KEY.encode(), params_str.encode(), digestmod=sha256).hexdigest()
    return signature, params_str

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
    logging.info(f"[BINGX] 🔄 Отправка запроса на BingX API: {url}")
    response = requests.get(url, headers=headers)
    try:
        data = response.json()
        logging.info(f"[BINGX] 📥 Ответ от BingX: {data}")
        return data
    except Exception:
        logging.exception("[BINGX] ❌ Ошибка при обработке JSON")
        return {"code": -1, "msg": "INVALID_JSON", "data": {}}

def find_uid_info(uid: str) -> dict:
    logging.info(f"[BINGX] 🔍 Поиск UID {uid} в списке рефералов")
    page = 1
    while True:
        result = get_referrals_page(page_index=page)
        if result.get("code") != 0:
            logging.warning("[BINGX] ⚠️ Ошибка или пустой ответ от BingX API")
            return {"found": False}
        data = result.get("data", {})
        referrals = data.get("list", [])
        if not isinstance(referrals, list):
            logging.warning("[BINGX] ❌ Неверный формат данных BingX")
            return {"found": False}
        for ref in referrals:
            if isinstance(ref, dict) and str(ref.get("uid")) == str(uid):
                logging.info(f"[BINGX] ✅ UID найден среди рефералов")
                return {
                    "found": True,
                    "kyc": ref.get("kycResult", False)
                }
        if len(referrals) < 50:
            break
        page += 1
    logging.info("[BINGX] ❌ UID не найден среди рефералов")
    return {"found": False}

def link_bingx_uid(telegram_id: str, uid: str) -> dict:
    logging.info(f"[BINGX] ▶️ Запрос /link-uid | Telegram ID: {telegram_id} | UID: {uid}")
    db = get_db_client()
    if not db:
        logging.error("[BINGX] ❌ Ошибка подключения к Firebase")
        return {"status": "error", "message": "DATABASE_ERROR"}
    
    ref_info = find_uid_info(uid)
    if not ref_info["found"]:
        logging.warning("[BINGX] ❌ UID не найден в списке рефералов")
        return {"status": "error", "message": "ERROR_NOT_FOUND"}
    
    users_ref = db.collection("telegram_users")
    user_ref = users_ref.document(telegram_id)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        logging.error("[BINGX] ❌ Пользователь не найден в Firestore")
        return {"status": "error", "message": "USER_NOT_FOUND"}

    logging.info(f"[BINGX] 🔄 Проверка использования UID другими пользователями")
    conflicting = users_ref.where("bingx_uid", "==", uid).stream()
    for doc in conflicting:
        if doc.id != telegram_id:
            logging.warning(f"[BINGX] ⚠️ UID {uid} уже привязан к другому пользователю: {doc.id}")
            return {"status": "error", "message": "ERROR_TAKEN"}

    # Привязка UID
    update_data = {"bingx_uid": uid}
    if ref_info.get("kyc", False):
        update_data["bingx_kyc"] = "KYC"
    user_ref.set(update_data, merge=True)
    logging.info(f"[BINGX] ✅ UID {uid} привязан к пользователю {telegram_id}, KYC: {update_data.get('bingx_kyc')}")

    now = datetime.now(timezone.utc)

    # Проверка флага bingx4days
    user_data = user_doc.to_dict()
    if user_data.get("bingx4days", False):
        logging.info("[BINGX] ⚠️ Бонус уже начислен ранее")
        _write_alerts_and_messages(user_ref, telegram_id,
            "🎉 UID BingX успешно привязан. 🎁 Бонус 4 дня уже был начислен ранее.")
        return {"status": "success", "telegram_id": telegram_id, "uid": uid}

    # Проверка истории использования UID
    logging.info("[BINGX] 🔍 Проверка истории использования UID в subscriptionHistory")
    for other_user in users_ref.stream():
        if other_user.id == telegram_id:
            continue
        history_ref = other_user.reference.collection("subscriptionHistory")
        used = list(history_ref
            .where("shopID", "==", "4bingxAihermesPro")
            .where("bingxuid", "==", uid)
            .limit(1).stream())
        if used:
            logging.warning(f"[BINGX] UID {uid} уже использовался ранее")
            _write_alerts_and_messages(user_ref, telegram_id,
                "⚠️ UID BingX использован ранее. 🎁 Бонус в 4 дня не предоставляется.")
            return {"status": "success", "telegram_id": telegram_id, "uid": uid}

    # Начисление бонуса
    logging.info("[BINGX] 🎁 Начисление бонуса в 4 дня подписки")
    subs_ref = user_ref.collection("subscriptions")
    target_sub = None
    for sub in subs_ref.stream():
        if sub.to_dict().get("subscription_type") == "AIHermesPRO":
            target_sub = sub
            break

    end_date = now + timedelta(days=4)
    if target_sub:
        old_end = target_sub.to_dict().get("end_date")
        logging.info(f"[BINGX] 📅 Текущая дата окончания: {old_end}")
        if isinstance(old_end, datetime) and old_end > now:
            end_date = old_end + timedelta(days=4)
        subs_ref.document(target_sub.id).update({"end_date": end_date})
        logging.info(f"[BINGX] 🔄 Подписка продлена до {end_date}")
    else:
        subs_ref.document().set({
            "subscription_type": "AIHermesPRO",
            "end_date": end_date,
            "tvEndData": False
        })
        logging.info(f"[BINGX] 🆕 Создана новая подписка до {end_date}")

    # История
    logging.info("[BINGX] 🧾 Добавление записи в subscriptionHistory")
    user_ref.collection("subscriptionHistory").add({
        "name": "4 дня BingX AIHermesPro",
        "price": 0,
        "purchaseDate": now,
        "shopID": "4bingxAihermesPro",
        "bingxuid": uid
    })

    # Уведомления
    _write_alerts_and_messages(user_ref, telegram_id,
        "🎉 Спасибо за регистрацию на бирже BingX! 🎁 Вам начислены 4 дня подписки на AIHermesPro!")

    # Флаг бонуса
    user_ref.update({"bingx4days": True})
    logging.info(f"[BINGX] ✅ Установлен флаг bingx4days=true для {telegram_id}")

    return {"status": "success", "telegram_id": telegram_id, "uid": uid}

def _write_alerts_and_messages(user_ref, telegram_id, message_text: str):
    now = datetime.now(timezone.utc)
    logging.info(f"[BINGX] 🔔 Отправка уведомления: {message_text}")
    user_ref.collection("alerts").add({
        "message": message_text,
        "read": False,
        "timestamp": now,
        "type": 1
    })
    db = get_db_client()
    db.collection("messages").add({
        "bot_name": "bssbot",
        "created_at": now,
        "memo": {"text": message_text},
        "image_url": BONUS_IMAGE_URL,
        "status": "pending",
        "telegram_id": telegram_id
    })
    logging.info(f"[BINGX] 💬 Сообщение создано в messages")
