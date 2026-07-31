"""TripCraft 后端入口 — FastAPI"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.models import init_db, SessionLocal, POI
from api import generate, verify, feedback, pois, chat
from services.rag_service import build_index_from_pois, is_index_ready

app = FastAPI(title="TripCraft API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(generate.router)
app.include_router(verify.router)
app.include_router(feedback.router)
app.include_router(pois.router)
app.include_router(chat.router)


@app.on_event("startup")
def startup():
    init_db()

    # 构建 RAG 向量索引
    if not is_index_ready():
        db = SessionLocal()
        all_pois = db.query(POI).all()
        poi_list = [
            {
                "city": p.city, "name": p.name, "category": p.category,
                "lat": p.lat, "lng": p.lng, "address": p.address,
                "cost": p.cost, "duration": p.duration, "note": p.note,
                "rating": p.rating,
            }
            for p in all_pois
        ]
        db.close()
        if poi_list:
            build_index_from_pois(poi_list)


@app.get("/")
def root():
    return {"name": "TripCraft API", "version": "2.0.0", "docs": "/docs"}