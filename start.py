# filename: start.py
import os, sys, base64, subprocess
from pathlib import Path

# 1) Подтянуть .env (если есть)
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env загружен")
except Exception:
    print("ℹ️ python-dotenv не найден или .env отсутствует — пропускаю")

# 2) Если есть GOOGLE_CREDENTIALS_BASE64 — разархивируем во временный файл
creds_b64 = os.environ.get("GOOGLE_CREDENTIALS_BASE64")
creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

if creds_b64 and not creds_path:
    tmp_path = "/tmp/google_credentials.json"
    Path(tmp_path).write_bytes(base64.b64decode(creds_b64))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp_path
    print(f"🔐 Firebase key из BASE64 записан в {tmp_path}")

elif creds_path and Path(creds_path).exists():
    print(f"🔐 Использую GOOGLE_APPLICATION_CREDENTIALS={creds_path}")
else:
    print("⚠️ Ключ Firebase не найден: ни GOOGLE_CREDENTIALS_BASE64, ни корректный GOOGLE_APPLICATION_CREDENTIALS")

# 3) Стартуем uvicorn
app_module = os.environ.get("APP_MODULE", "main:app")
host = os.environ.get("HOST", "0.0.0.0")
port = os.environ.get("PORT", "8000")

print(f"🚀 Запуск {app_module} на http://{host}:{port}")
try:
    # check=False, чтобы не бросать исключение при остановке
    subprocess.run(["uvicorn", app_module, "--host", host, "--port", port], check=False)
except KeyboardInterrupt:
    print("🛑 Остановлено пользователем (Ctrl+C)")
    sys.exit(0)
