# filename: main.py
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from services.firebase_service import get_db_client  # унифицированный доступ к Firestore

# 🟢 Логи в STDOUT (чтобы Railway не красил их в error)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("BssMiniApp")

# Импорт роутеров
from routers import (
    wallets_router,
    subscriptions_router,
    checkin_router,
    blofin_router,
    bybit_router,
    user_router,
    bingx_router,
    auth_router,
)
# 🔹 SD-роутер подключаем напрямую (не зависит от __all__ в routers/__init__.py)
from routers.sd_router import router as sd_router

app = FastAPI(
    title="BssMiniApp API",
    description="Сервис для генерации кошельков и обработки API для BssMiniApp.",
    version="1.0.0",
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
logger.info("🔗 Подключение роутеров...")
app.include_router(wallets_router.router, prefix="/api", tags=["Wallets"])
app.include_router(subscriptions_router.router, prefix="/api", tags=["Subscriptions"])
app.include_router(checkin_router.router, prefix="/api", tags=["Check-in"])
app.include_router(blofin_router.router, prefix="/api/blofin", tags=["BloFin"])
app.include_router(bybit_router.router, prefix="/api/bybit", tags=["Bybit"])
app.include_router(user_router.router, prefix="/api", tags=["Users"])
app.include_router(bingx_router.router, prefix="/api/bingx", tags=["BingX"])
app.include_router(auth_router.router, prefix="/api", tags=["Auth"])
# 🔹 Новый сервис-деск роутер — /api/sd/notify
app.include_router(sd_router, prefix="/api", tags=["ServiceDesk"])
logger.info("✅ Все роутеры подключены")


@app.get("/", tags=["Root"])
def read_root():
    """Корневой эндпоинт."""
    return {"status": "ok", "message": "Welcome to BssMiniApp API"}


@app.get("/health", tags=["Health"])
def health():
    """Лёгкий healthcheck без обращения к БД."""
    return {"status": "ok"}


# Локальный запуск (на Railway не используется)
if __name__ == "__main__":
    logger.info("🚀 Запуск BssMiniApp API (локально)")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
