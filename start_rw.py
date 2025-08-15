# start_railway.py
import os
import base64
import subprocess

print("🚀 Запуск usersBssAPI на Railway...")

creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
if not creds_b64:
    raise RuntimeError("❌ GOOGLE_CREDENTIALS_BASE64 не указаны")

# Сохраняем ключ в /tmp
creds_path = "/tmp/google_credentials.json"
with open(creds_path, "wb") as f:
    f.write(base64.b64decode(creds_b64))

# Устанавливаем переменные
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

print(f"✅ Ключ сохранён в {creds_path}")
print("🌐 Запуск FastAPI через uvicorn...")

subprocess.run(["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"], check=True)
