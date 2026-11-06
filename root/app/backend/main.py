import uvicorn
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import ALLOWED_ORIGINS
from .database import create_db
from .routers import auth, commerce, reviews, store_operations, stores, webhooks

app = FastAPI(title="TokTok API")
app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
create_db()
UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

app.include_router(store_operations.router)
app.include_router(auth.router)
app.include_router(stores.router)
app.include_router(commerce.router)
app.include_router(reviews.router)
app.include_router(webhooks.router)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
