# filename: services/subscription_service.py
import os
import logging
from datetime import datetime, timedelta, timezone
from services.firebase_service import get_db_client
from firebase_admin import firestore
import requests

# Внешние API базовые URL из окружения
BSSBIN_API_URL = os.getenv("BSSBIN_API_URL")      # для AIHermesPRO
BSSBYB_API_URL = os.getenv("BSSBYB_API_URL")      # для BybitAIHermesPRO


def purchase_subscription(telegram_id: str, shop_id: str) -> dict:
    """
    Основная функция для обработки покупки подписки.
    Выполняет все операции в рамках одной атомарной транзакции.
    После успешной записи в БД вызывает внешний API партнёра.
    """
    db = get_db_client()
    if not db:
        logging.error("Не удалось получить клиент БД для покупки подписки.")
        return {"status": "error", "message": "Database connection failed."}

    try:
        transaction = db.transaction()
        tx_result = _update_in_transaction(transaction, db, telegram_id, shop_id)

        # Если транзакция прошла успешно — вызываем внешний API по типу подписки
        if tx_result.get("status") == "success":
            subscription_type = tx_result.get("subscription_type")
            end_date = tx_result.get("end_date")  # datetime (UTC)
            api_call = _notify_partner_api(subscription_type, telegram_id, end_date)
            tx_result["partner_api"] = api_call

        return tx_result

    except Exception as e:
        logging.exception(f"Критическая ошибка при покупке подписки для user {telegram_id}: {e}")
        return {"status": "error", "message": str(e)}


@firestore.transactional
def _update_in_transaction(transaction, db, telegram_id: str, shop_id: str) -> dict:
    """Внутренняя функция, выполняющая все действия в рамках транзакции Firestore."""

    # --- ШАГ 1: СНАЧАЛА ВСЕ ОПЕРАЦИИ ЧТЕНИЯ ---

    user_ref = db.collection("telegram_users").document(telegram_id)
    shop_ref = db.collection("shop").document(shop_id)

    user_snapshot = user_ref.get(transaction=transaction)
    shop_snapshot = shop_ref.get(transaction=transaction)

    if not user_snapshot.exists or not shop_snapshot.exists:
        return {"status": "error", "message": "Пользователь или товар не найден."}

    user_data = user_snapshot.to_dict()
    shop_data = shop_snapshot.to_dict()

    # Также выполняем чтение подписки сразу
    subscription_type = shop_data.get("stock")
    subscriptions_query = (
        user_ref.collection("subscriptions")
        .where("subscription_type", "==", subscription_type)
        .limit(1)
    )
    sub_docs = list(subscriptions_query.stream(transaction=transaction))

    # --- ШАГ 2: ЗАТЕМ ВСЯ ЛОГИКА И ПРОВЕРКИ ---

    balance_usdt = user_data.get("balance_usdt", 0.0)
    checkin_date = user_data.get("checkin_date")
    dynamic_balance = balance_usdt

    if checkin_date and datetime.now(timezone.utc) < checkin_date:
        seconds_left = (checkin_date - datetime.now(timezone.utc)).total_seconds()
        if seconds_left > 0:
            dynamic_balance = balance_usdt - (seconds_left * 0.000024)

    price = shop_data.get("price", 0.0)
    if dynamic_balance < price:
        shortage = price - dynamic_balance
        return {"status": "error", "message": f"Недостаточно средств. Не хватает {shortage:.2f} USDT."}

    # --- ШАГ 3: В КОНЦЕ ВСЕ ОПЕРАЦИИ ЗАПИСИ ---

    # 3.1 Списываем средства
    new_balance = balance_usdt - price
    transaction.update(user_ref, {"balance_usdt": new_balance})

    # 3.2 Обновляем или создаем подписку
    duration_days = shop_data.get("duration", 0)
    now = datetime.now(timezone.utc)

    # итоговая дата окончания подписки, которую вернём наружу
    new_end_date: datetime

    if sub_docs:
        sub_doc_ref = sub_docs[0].reference
        sub_end_date = sub_docs[0].to_dict().get("end_date", now)
        start_date = sub_end_date if isinstance(sub_end_date, datetime) and sub_end_date > now else now
        new_end_date = start_date + timedelta(days=duration_days)
        # ✅ ДОБАВЛЕНО: обновляем end_date + выставляем флаги tv*
        transaction.update(sub_doc_ref, {
            "end_date": new_end_date,
            "tvEndData": False,   # bool
            "tvStatus": "start",  # string
        })
    else:
        new_end_date = now + timedelta(days=duration_days)
        new_sub_ref = user_ref.collection("subscriptions").document()
        # ✅ ДОБАВЛЕНО: создаём подписку с полями tv*
        transaction.set(new_sub_ref, {
            "subscription_type": subscription_type,
            "end_date": new_end_date,
            "tvEndData": False,   # bool
            "tvStatus": "start",  # string
        })

    # 3.3 Делаем запись в историю
    history_ref = user_ref.collection("subscriptionHistory").document()
    transaction.set(history_ref, {
        "shopID": shop_id,
        "purchaseDate": now,
        "price": price,
        "name": shop_data.get("name"),
        "stock": subscription_type
    })

    logging.info(f"Транзакция для {telegram_id} успешно подготовлена.")
    # Вернём ещё и данные для внешнего вызова
    return {
        "status": "success",
        "message": "Подписка успешно приобретена.",
        "subscription_type": subscription_type,
        "end_date": new_end_date,  # datetime (UTC)
    }


def _notify_partner_api(subscription_type: str, telegram_id: str, end_date_utc: datetime) -> dict:
    """
    Вызывает внешний API в зависимости от типа подписки.
    Форматирует end_date в ISO 8601 со смещением +03:00 (как в тесте).
    """
    try:
        if subscription_type == "AIHermesPRO":
            base_url = BSSBIN_API_URL
        elif subscription_type == "BybitAIHermesPRO":
            base_url = BSSBYB_API_URL
        else:
            logging.info(f"[PARTNER_API] Для типа {subscription_type} внешний вызов не настроен — пропуск.")
            return {"called": False, "reason": "unsupported_subscription_type"}

        if not base_url:
            logging.error(f"[PARTNER_API] Не задан URL для {subscription_type} (env).")
            return {"called": False, "reason": "missing_base_url"}

        # Приводим дату к +03:00 и форматируем как в примере:
        # "2025-07-29T14:28:00+03:00"
        tz_plus_3 = timezone(timedelta(hours=3))
        end_date_local = end_date_utc.astimezone(tz_plus_3).isoformat()

        url = f"{base_url.rstrip('/')}/new-subscription"
        payload = {
            "telegram_id": str(telegram_id),
            "end_date": end_date_local,
        }

        logging.info(f"[PARTNER_API] POST {url} payload={payload}")
        resp = requests.post(url, json=payload, timeout=10)

        ok = 200 <= resp.status_code < 300
        if ok:
            logging.info(f"[PARTNER_API] ✅ {subscription_type} -> {resp.status_code}")
        else:
            logging.warning(f"[PARTNER_API] ⚠️ {subscription_type} -> {resp.status_code}, body={resp.text}")

        return {
            "called": True,
            "url": url,
            "status_code": resp.status_code,
            "ok": ok,
        }

    except Exception as e:
        logging.exception("[PARTNER_API] ❌ Ошибка вызова внешнего сервиса")
        return {"called": True, "ok": False, "error": str(e)}
