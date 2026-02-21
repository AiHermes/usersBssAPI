# happyh.py
import os
import logging
from datetime import datetime, timedelta, timezone
import requests
from dotenv import load_dotenv

from config import get_db_client  # используем ваш отлаженный клиент

load_dotenv()

# --- Настройки ---
BSSBIN_BASE_URL = os.getenv("BSSBIN_API_URL", "https://bssbin-production.up.railway.app/")
BSSBIN_ENDPOINT = "/new-subscription"
REQUEST_TIMEOUT_SEC = 3

# --- Логгер ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)

def _normalize_base_url(url: str) -> str:
    if not url:
        return ""
    return url.rstrip("/")

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _utc_plus2_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=2)))

def _iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def _call_bssbin_new_subscription(telegram_id: str, end_date_utc: datetime) -> tuple[bool, str]:
    base = _normalize_base_url(BSSBIN_BASE_URL)
    url = f"{base}{BSSBIN_ENDPOINT}"
    payload = {
        "telegram_id": str(telegram_id),
        "end_date": _iso(end_date_utc),
    }

    logging.info(f"📡 [BSSBIN] POST {url}")
    logging.info(f"📦 [BSSBIN] Payload: {payload}")

    try:
        r = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SEC)
        text = r.text.strip()
        logging.info(f"📨 [BSSBIN] Ответ: {r.status_code} {text}")
        if 200 <= r.status_code < 300:
            return True, text
        return False, text
    except requests.exceptions.Timeout:
        msg = "timeout"
        logging.warning(f"⏱ [BSSBIN] Таймаут при вызове {url}")
        return False, msg
    except Exception as e:
        logging.exception(f"❌ [BSSBIN] Ошибка вызова {url}: {e}")
        return False, str(e)

def _find_aihermespro_subscription_doc(subs_collection) -> tuple[str | None, dict | None]:
    """
    Ищем документ в подколлекции subscriptions, где subscription_type == 'AIHermesPRO'
    Возвращаем (doc_id, doc_dict) или (None, None).
    """
    for doc in subs_collection.stream():
        data = doc.to_dict() or {}
        if data.get("subscription_type") == "AIHermesPRO":
            return doc.id, data
    return None, None

def process_user(user_ref, telegram_id: str) -> None:
    """
    Для active пользователя:
    - ищем подписку AIHermesPRO в подколлекции subscriptions
    - если end_date <= now или отсутствует => ставим now(UTC+2)+1h (сохраняем UTC)
    - вызываем bssbin /new-subscription
    """
    now_utc = _utc_now()
    now_plus2 = _utc_plus2_now()

    subs_collection = user_ref.collection("subscriptions")
    sub_doc_id, sub_data = _find_aihermespro_subscription_doc(subs_collection)

    old_end = None
    if sub_data:
        old_end = sub_data.get("end_date")

    logging.info(f"   🧾 subscription_type=AIHermesPRO doc_id={sub_doc_id or '—'}")
    logging.info(f"   📅 end_date (старое): {old_end}")

    # Определяем, активна ли подписка
    active = False
    if isinstance(old_end, datetime):
        # Firestore Timestamp приходит как datetime (обычно tz-aware UTC)
        try:
            if old_end.tzinfo is None:
                old_end = old_end.replace(tzinfo=timezone.utc)
            active = old_end > now_utc
        except Exception:
            active = False

    if active:
        logging.info("   ✅ Подписка уже активна — пропускаю")
        return

    # Нужно выставить новую дату: now(UTC+2)+1h, но сохраняем в UTC
    new_end_plus2 = now_plus2 + timedelta(hours=1)
    new_end_utc = new_end_plus2.astimezone(timezone.utc)

    logging.info(f"   🔄 Обновляю end_date -> {new_end_utc} (UTC) | (local UTC+2: {new_end_plus2})")

    # Обновляем/создаём документ в подколлекции subscriptions
    try:
        if sub_doc_id:
            # Меняем ТОЛЬКО end_date, остальные поля (например tvEndData) не трогаем
            subs_collection.document(sub_doc_id).update({"end_date": new_end_utc})
            logging.info("   ✅ Firestore: end_date обновлён (update)")
        else:
            # Создаём новую подписку (минимальный корректный формат)
            # tvEndData можно ставить False как дефолт, чтобы формат был как у вас в примерах
            subs_collection.document().set({
                "subscription_type": "AIHermesPRO",
                "end_date": new_end_utc,
                "tvEndData": False
            })
            logging.info("   ✅ Firestore: подписка создана (set)")
    except Exception as e:
        logging.exception(f"   ❌ Firestore: ошибка обновления подписки: {e}")
        return

    # Вызываем внешний API, чтобы обновился кеш/сигналы
    ok, _ = _call_bssbin_new_subscription(telegram_id, new_end_utc)
    if ok:
        logging.info("   ✅ BSSBIN: обновление выполнено")
    else:
        logging.warning("   ⚠️ BSSBIN: не удалось обновить (см. лог выше)")

def main():
    logging.info("[HAPPYH] Старт скрипта: обработка всех telegram_users со status_tgbin=active")
    db = get_db_client()
    if not db:
        logging.error("[HAPPYH] ❌ Не удалось получить Firestore client (get_db_client вернул None)")
        return

    users_ref = db.collection("telegram_users")

    processed = 0
    skipped = 0
    errors = 0

    try:
        for user_doc in users_ref.stream():
            telegram_id = user_doc.id
            data = user_doc.to_dict() or {}
            status_tgbin = data.get("status_tgbin")

            logging.info(f"\n👤 Пользователь: {telegram_id} | status_tgbin={status_tgbin}")

            if status_tgbin != "active":
                logging.info("   ⏭ Пропуск (не active)")
                skipped += 1
                continue

            try:
                process_user(users_ref.document(telegram_id), telegram_id)
                processed += 1
            except Exception as e:
                logging.exception(f"   ❌ Ошибка обработки пользователя {telegram_id}: {e}")
                errors += 1

    except Exception as e:
        logging.exception(f"[HAPPYH] ❌ Ошибка чтения telegram_users: {e}")
        return

    logging.info("\n[HAPPYH] Готово.")
    logging.info(f"✅ обработано active: {processed}")
    logging.info(f"⏭ пропущено: {skipped}")
    logging.info(f"❌ ошибок: {errors}")
    logging.info("⚠️ Напоминание: проверь Firestore Security Rules/permissions для subscriptions и messages/alerts.")

if __name__ == "__main__":
    main()
