# filename: services/user_service.py
from typing import Optional, Tuple, Dict
from services.wallet_service import create_new_wallet_for_user
from services.firebase_service import get_db_client

USERS_COLLECTION = "telegram_users"
db = get_db_client()

def find_user_and_status(telegram_id: int) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict]]:
    """
    Возвращает:
      (exists, status_tgbss, user_doc_path, user_data)

    Логика поиска:
      A) Документ с id = str(telegram_id)
      B) Документ, где поле 'id' == str(telegram_id) (строка)

    Дополнительно:
      - Если status_tgbss активен и bnb_wallet_address отсутствует, создаёт новый кошелёк.
    """
    col = db.collection(USERS_COLLECTION)
    print(f"[FIRESTORE] Поиск пользователя в коллекции '{USERS_COLLECTION}' по Telegram ID: {telegram_id}")

    # A) docId = str(telegram_id)
    doc_ref = col.document(str(telegram_id))
    snap = doc_ref.get()
    if snap.exists:
        data = snap.to_dict() or {}
        print(f"[FIRESTORE] Найден документ по docId. Путь: {doc_ref.path}, status_tgbss={data.get('status_tgbss')}")

        _maybe_create_wallet(str(telegram_id), data)
        return True, data.get("status_tgbss"), doc_ref.path, data

    # B) поле 'id' как строка
    q = col.where("id", "==", str(telegram_id)).limit(1).stream()
    for d in q:
        data = d.to_dict() or {}
        print(f"[FIRESTORE] Найден документ по полю 'id'. Путь: {d.reference.path}, status_tgbss={data.get('status_tgbss')}")

        _maybe_create_wallet(d.id, data)  # d.id — это docId
        return True, data.get("status_tgbss"), d.reference.path, data

    print("[FIRESTORE] Пользователь не найден.")
    return False, None, None, None


def _maybe_create_wallet(user_id: str, data: Dict) -> None:
    """
    Если статус активен, а bnb_wallet_address отсутствует или пустой — создаёт кошелёк.
    """
    status = data.get("status_tgbss")
    wallet_address = data.get("bnb_wallet_address")

    if _is_status_active(status) and not wallet_address:
        print(f"[WALLET] У пользователя {user_id} активен статус, но нет кошелька — создаём...")
        res = create_new_wallet_for_user(user_id)
        if res and res.get("status") == "success":
            print(f"[WALLET] Кошелёк создан: {res['address']}")
        elif res and res.get("status") == "exists":
            print(f"[WALLET] Кошелёк уже есть: {res['address']}")
        else:
            print(f"[WALLET] Не удалось создать кошелёк для {user_id}.")


def _is_status_active(value) -> bool:
    """
    Приводим к логике: True, 'active', 'enabled', 'true', 'on', 1 — активный статус.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"active", "enabled", "true", "on"}
    if isinstance(value, (int, float)):
        return value == 1
    return False
