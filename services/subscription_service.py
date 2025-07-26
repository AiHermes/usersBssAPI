# services/subscription_service.py
import logging
from datetime import datetime, timedelta, timezone
from config import get_db_client
from firebase_admin import firestore

def purchase_subscription(telegram_id: str, shop_id: str) -> dict:
    """
    Основная функция для обработки покупки подписки.
    Выполняет все операции в рамках одной атомарной транзакции.
    """
    db = get_db_client()
    if not db:
        logging.error("Не удалось получить клиент БД для покупки подписки.")
        return {"status": "error", "message": "Database connection failed."}

    try:
        transaction = db.transaction()
        result = _update_in_transaction(transaction, db, telegram_id, shop_id)
        return result
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
    subscriptions_query = user_ref.collection("subscriptions").where("subscription_type", "==", subscription_type).limit(1)
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
    
    if sub_docs:
        sub_doc_ref = sub_docs[0].reference
        sub_end_date = sub_docs[0].to_dict().get("end_date", now)
        start_date = sub_end_date if sub_end_date > now else now
        new_end_date = start_date + timedelta(days=duration_days)
        transaction.update(sub_doc_ref, {"end_date": new_end_date})
    else:
        new_end_date = now + timedelta(days=duration_days)
        new_sub_ref = user_ref.collection("subscriptions").document()
        transaction.set(new_sub_ref, {
            "subscription_type": subscription_type,
            "end_date": new_end_date
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
    return {"status": "success", "message": "Подписка успешно приобретена."}