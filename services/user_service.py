# filename: services/user_service.py
from typing import Optional, Tuple, Dict
from google.cloud import firestore

USERS_COLLECTION = "telegram_users"
db = firestore.Client()

def find_user_and_status(telegram_id: int) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict]]:
    """
    Возвращает:
      (exists, status_tgbss, user_doc_path, user_data)

    Логика поиска:
      A) Документ с id = str(telegram_id)
      B) Документ, где поле 'id' == str(telegram_id) (строка)
    """
    col = db.collection(USERS_COLLECTION)
    print(f"[FIRESTORE] Поиск пользователя в коллекции '{USERS_COLLECTION}' по Telegram ID: {telegram_id}")

    # A) docId = str(telegram_id)
    doc_ref = col.document(str(telegram_id))
    snap = doc_ref.get()
    if snap.exists:
        data = snap.to_dict() or {}
        print(f"[FIRESTORE] Найден документ по docId. Путь: {doc_ref.path}, status_tgbss={data.get('status_tgbss')}")
        return True, data.get("status_tgbss"), doc_ref.path, data

    # B) поле 'id' как строка
    q = col.where("id", "==", str(telegram_id)).limit(1).stream()
    for d in q:
        data = d.to_dict() or {}
        print(f"[FIRESTORE] Найден документ по полю 'id'. Путь: {d.reference.path}, status_tgbss={data.get('status_tgbss')}")
        return True, data.get("status_tgbss"), d.reference.path, data

    print("[FIRESTORE] Пользователь не найден.")
    return False, None, None, None
