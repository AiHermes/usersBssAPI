# services/security_service.py
import os
import logging
from google.cloud import secretmanager
from google.api_core import exceptions

def store_private_key(user_id: str, private_key: str) -> str | None:
    try:
        project_id = os.getenv("GCP_PROJECT_ID")
        if not project_id:
            logging.error("[SECURITY_SERVICE] GCP_PROJECT_ID не найден.")
            return None

        client = secretmanager.SecretManagerServiceClient()
        secret_id = f"user-{user_id}-bnb-key"
        parent = f"projects/{project_id}"
        secret_path = f"{parent}/secrets/{secret_id}"
        
        logging.info(f"[SECURITY_SERVICE] Проверяю/создаю секрет: {secret_path}")

        try:
            client.create_secret(
                request={"parent": parent, "secret_id": secret_id, "secret": {"replication": {"automatic": {}}}}
            )
            logging.info(f"[SECURITY_SERVICE] Создан новый секрет: {secret_id}")
        except exceptions.AlreadyExists:
            logging.warning(f"[SECURITY_SERVICE] Секрет {secret_id} уже существует. Будет добавлена новая версия.")
            pass

        payload = private_key.encode("UTF-8")
        version = client.add_secret_version(
            request={"parent": secret_path, "payload": {"data": payload}}
        )

        logging.info(f"✅ [SECURITY_SERVICE] Ключ для user_id: {user_id} сохранен (версия {version.name.split('/')[-1]})")
        
        return secret_path

    except Exception as e:
        logging.exception(f"❌ [SECURITY_SERVICE] Не удалось сохранить ключ для user_id {user_id}: {e}")
        return None