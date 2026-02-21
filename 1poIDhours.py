# filename: 1poID.py
import os
import logging
from datetime import datetime, timedelta, timezone
import requests

from config import get_db_client

logging.basicConfig(level=logging.INFO, format="%(message)s")

# --- НАСТРОЙКИ ---
TELEGRAM_ID = "7639116350"
SUBSCRIPTION_TYPE = "AIHermesPRO"
TZ_PLUS2 = timezone(timedelta(hours=2))

# В env у тебя: BSSBIN_API_URL=https://bssbin-production.up.railway.app/
BSSBIN_BASE_URL = os.getenv("BSSBIN_API_URL", "https://bssbin-production.up.railway.app/").strip()
if not BSSBIN_BASE_URL.endswith("/"):
    BSSBIN_BASE_URL += "/"

BSSBIN_NEW_SUB_URL = BSSBIN_BASE_URL + "new-subscription"


def call_bssbin_new_subscription(telegram_id: str, end_date_utc: datetime) -> None:
    payload = {
        "telegram_id": str(telegram_id),
        "end_date": end_date_utc.isoformat()
    }

    logging.info(f"📡 Вызываю bssbin: POST {BSSBIN_NEW_SUB_URL}")
    logging.info(f"📦 Payload: {payload}")

    try:
        resp = requests.post(BSSBIN_NEW_SUB_URL, json=payload, timeout=10)
        logging.info(f"📨 Ответ bssbin: {resp.status_code} {resp.text}")
    except requests.exceptions.Timeout:
        logging.warning("⏱ Таймаут при вызове bssbin /new-subscription")
    except Exception as e:
        logging.exception(f"❌ Ошибка вызова bssbin /new-subscription: {e}")


def main():
    db = get_db_client()
    if not db:
        logging.error("❌ Не удалось подключиться к Firestore (проверь GOOGLE_APPLICATION_CREDENTIALS).")
        return

    user_ref = db.collection("telegram_users").document(TELEGRAM_ID)
    user_snap = user_ref.get()

    if not user_snap.exists:
        logging.error(f"❌ Пользователь {TELEGRAM_ID} не найден в telegram_users.")
        return

    now_plus2 = datetime.now(TZ_PLUS2)
    now_utc = now_plus2.astimezone(timezone.utc)

    logging.info(f"🕒 Текущее время (UTC+2): {now_plus2}")
    logging.info(f"🕒 Текущее время (UTC):   {now_utc}")

    subs_col = user_ref.collection("subscriptions")

    # Ищем подписку AIHermesPRO в подколлекции subscriptions
    target_ref = None
    target_data = None

    for snap in subs_col.stream():
        data = snap.to_dict() or {}
        if data.get("subscription_type") == SUBSCRIPTION_TYPE:
            target_ref = snap.reference
            target_data = data
            break

    if target_ref:
        current_end = target_data.get("end_date")
        logging.info(f"📅 Текущая end_date: {current_end}")

        if isinstance(current_end, datetime):
            if current_end.tzinfo is None:
                current_end = current_end.replace(tzinfo=timezone.utc)

            if current_end > now_utc:
                logging.info("✅ Подписка уже активна (end_date позже текущего времени).")
                return
        else:
            logging.info("⚠️ end_date отсутствует/неверного типа — назначаю заново.")
    else:
        logging.info("⚠️ Подписка AIHermesPRO не найдена — создам новый документ в подколлекции subscriptions.")

    # Если подписка истекла/не найдена — ставим now(+2) + 1 час, сохраняем в UTC
    new_end_plus2 = now_plus2 + timedelta(hours=1)
    new_end_utc = new_end_plus2.astimezone(timezone.utc)

    if target_ref:
        logging.info(f"🔄 Обновляю end_date -> {new_end_utc} (UTC)")
        # Меняем ТОЛЬКО end_date, tvEndData не трогаем
        target_ref.update({"end_date": new_end_utc})
    else:
        logging.info(f"🆕 Создаю подписку AIHermesPRO с end_date -> {new_end_utc} (UTC)")
        # При создании делаем формат как в системе (tvEndData задаём явно)
        subs_col.document().set({
            "subscription_type": SUBSCRIPTION_TYPE,
            "end_date": new_end_utc,
            "tvEndData": False
        })

    logging.info(f"✅ Firestore обновлён: end_date = {new_end_utc} (UTC)")

    # Вызов внешнего API для обновления кеша/сигналов
    call_bssbin_new_subscription(TELEGRAM_ID, new_end_utc)

    # Напоминание по правилам доступа
    logging.info("⚠️ Напоминание: проверь Firestore Security Rules/permissions для subscriptions и messages/alerts.")


if __name__ == "__main__":
    main()
