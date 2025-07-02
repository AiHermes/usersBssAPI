from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import get_db_client
from routers import wallets_router, subscriptions_router

# --- УБЕДИТЕСЬ, ЧТО ЭТОТ БЛОК НА МЕСТЕ ---
# Он создает основной экземпляр приложения под именем 'app'
app = FastAPI(
    title="BssMiniApp API",
    description="Сервис для генерации кошельков и обработки API для BssMiniApp.",
    version="1.0.0"
)
# ----------------------------------------

# Блок настройки CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(wallets_router.router, prefix="/api", tags=["Wallets"])
app.include_router(subscriptions_router.router, prefix="/api", tags=["Subscriptions"])


@app.get("/", tags=["Root"])
def read_root():
    """Корневой эндпоинт для проверки работы сервиса."""
    db = get_db_client()
    if not db:
        return {"status": "error", "message": "Failed to connect to Database"}
    return {"status": "ok", "message": "Welcome to BssMiniApp API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)