import os
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("BLOFIN_API_KEY")
API_SECRET = os.getenv("BLOFIN_API_SECRET")
PASSPHRASE = os.getenv("BLOFIN_API_PASSPHRASE")

print("KEY:", API_KEY)
print("SECRET:", API_SECRET)
print("PASSPHRASE:", PASSPHRASE)

# Проверка времени
timestamp = str(int(time.time() * 1000))
print("Timestamp (ms):", timestamp)
print("Datetime (UTC):", time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(int(timestamp) / 1000)))
