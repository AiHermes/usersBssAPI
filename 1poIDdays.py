# filename: 1poIDdays.py
import os
import logging
from datetime import datetime, timedelta, timezone
import requests

from config import get_db_client
from services.services.deleted.user_service import create_initial_user_record

logging.basicConfig(level=logging.INFO, format="%(message)s")

# --- НАСТРОЙКИ ---
TELEGRAM_ID = "1124877396"  # можно оставить как есть: если doc-id другой, найдём по полю id/telegram_id
SUBSCRIPTION_TYPE = "AIHermesPRO"
TZ_PLUS2 = timezone(timedelta(hours=2))

ADD_DAYS = 1

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


def resolve_user_ref(users_ref, telegram_id: str):
    """
    Возвращает (user_ref, user_snap, resolved_doc_id) или (None, None, None)
    1) Пытаемся найти документ по doc-id == telegram_id
    2) Если не нашли — ищем по полям id == telegram_id или telegram_id == telegram_id
    """
    # 1) doc-id == telegram_id
    user_ref = users_ref.document(str(telegram_id))
    user_snap = user_ref.get()
    if user_snap.exists:
        logging.info(f"✅ Пользователь найден по doc-id: {user_ref.id}")
        return user_ref, user_snap, user_ref.id

    logging.warning(f"⚠️ Не найден по doc-id: {telegram_id}. Пробую поиск по полям id/telegram_id...")

    # 2) поиск по полю id
    try:
        q1 = list(users_ref.where("id", "==", str(telegram_id)).limit(1).stream())
        if q1:
            doc = q1[0]
            logging.info(f"✅ Пользователь найден по полю id: doc-id={doc.id}")
            return doc.reference, doc, doc.id
    except Exception:
        logging.exception("❌ Ошибка при поиске по полю id")

    # 3) поиск по полю telegram_id
    try:
        q2 = list(users_ref.where("telegram_id", "==", str(telegram_id)).limit(1).stream())
        if q2:
            doc = q2[0]
            logging.info(f"✅ Пользователь найден по полю telegram_id: doc-id={doc.id}")
            return doc.reference, doc, doc.id
    except Exception:
        logging.exception("❌ Ошибка при поиске по полю telegram_id")

    return None, None, None


def ensure_user_exists(users_ref, telegram_id: str):
    """
    Гарантирует существование пользователя.
    Если пользователя нет — создает через существующую процедуру.
    Возвращает (user_ref, user_snap, resolved_doc_id) или (None, None, None) при ошибке.
    """
    user_ref, user_snap, resolved_doc_id = resolve_user_ref(users_ref, telegram_id)
    if user_ref:
        return user_ref, user_snap, resolved_doc_id

    logging.warning(f"⚠️ Пользователь {telegram_id} не найден. Создаю новую запись...")
    create_result = create_initial_user_record(telegram_id=str(telegram_id))

    if create_result.get("status") == "error":
        logging.error(f"❌ Не удалось создать пользователя {telegram_id}: {create_result.get('message')}")
        return None, None, None

    # После создания повторно разрешаем ссылку,
    # чтобы поддержать единый формат поиска (doc-id / поля).
    user_ref, user_snap, resolved_doc_id = resolve_user_ref(users_ref, telegram_id)
    if not user_ref:
        logging.error(f"❌ Пользователь {telegram_id} был создан, но не найден при повторной проверке.")
        return None, None, None

    logging.info(f"✅ Пользователь {telegram_id} готов к обновлению подписки.")
    return user_ref, user_snap, resolved_doc_id


def main():
    db = get_db_client()
    if not db:
        logging.error("❌ Не удалось подключиться к Firestore (проверь GOOGLE_APPLICATION_CREDENTIALS).")
        return

    users_ref = db.collection("telegram_users")

    user_ref, user_snap, resolved_doc_id = ensure_user_exists(users_ref, TELEGRAM_ID)
    if not user_ref:
        logging.error(f"❌ Не удалось подготовить пользователя {TELEGRAM_ID} в telegram_users.")
        return

    now_plus2 = datetime.now(TZ_PLUS2)
    now_utc = now_plus2.astimezone(timezone.utc)

    logging.info(f"🕒 Текущее время (UTC+2): {now_plus2}")
    logging.info(f"🕒 Текущее время (UTC):   {now_utc}")

    subs_col = user_ref.collection("subscriptions")

    # Ищем подписку AIHermesPRO в подколлекции subscriptions
    target_ref = None
    target_data = None

    subs_docs = list(subs_col.stream())
    logging.info(f"📂 Найдено документов в subscriptions: {len(subs_docs)}")

    for snap in subs_docs:
        data = snap.to_dict() or {}
        if data.get("subscription_type") == SUBSCRIPTION_TYPE:
            target_ref = snap.reference
            target_data = data
            break

    # База для продления:
    # - если end_date > now => от end_date
    # - иначе => от now
    base_date_utc = now_utc

    if target_ref:
        current_end = target_data.get("end_date")
        logging.info(f"📅 Текущая end_date: {current_end}")

        if isinstance(current_end, datetime):
            if current_end.tzinfo is None:
                current_end = current_end.replace(tzinfo=timezone.utc)

            if current_end > now_utc:
                base_date_utc = current_end
                logging.info("✅ Подписка активна — продлеваю от текущей end_date")
            else:
                base_date_utc = now_utc
                logging.info("🔁 Подписка истекла — продлеваю от текущего времени")
        else:
            base_date_utc = now_utc
            logging.info("⚠️ end_date отсутствует/неверного типа — продлеваю от текущего времени")
    else:
        # ВАЖНО: если записей нет или нет AIHermesPRO — создаём новую
        logging.info("🆕 Подписка AIHermesPRO не найдена — создаю новый документ в subscriptions.")
        base_date_utc = now_utc

    new_end_utc = base_date_utc + timedelta(days=ADD_DAYS)

    if target_ref:
        logging.info(f"🔄 Обновляю end_date -> {new_end_utc} (UTC)  (+{ADD_DAYS} дней)")
        # Меняем ТОЛЬКО end_date, tvEndData не трогаем
        target_ref.update({"end_date": new_end_utc})
    else:
        logging.info(f"🆕 Создаю подписку AIHermesPRO с end_date -> {new_end_utc} (UTC)  (+{ADD_DAYS} дней)")
        subs_col.document().set({
            "subscription_type": SUBSCRIPTION_TYPE,
            "end_date": new_end_utc,
            "tvEndData": False
        })

    logging.info(f"✅ Firestore обновлён: end_date = {new_end_utc} (UTC)")

    # Вызов внешнего API для обновления кеша/сигналов
    call_bssbin_new_subscription(TELEGRAM_ID, new_end_utc)

    logging.info("⚠️ Напоминание: проверь Firestore Security Rules/permissions для subscriptions и messages/alerts.")


if __name__ == "__main__":
    main()
