"""TripCraft 后端入口 — FastAPI (v2 异步版)"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database.models import init_db, SessionLocal, POI
from api import generate, verify, feedback, pois, chat
from api import generate_stream, itineraries, share, weather, packing
from api import auth, pois_detail, user
from api.errors import TripCraftError, trip_error_handler
from services.rag_service import build_index_from_pois, is_index_ready
from utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    logger.info("TripCraft 启动中...")
    init_db()
    logger.info("数据库初始化完成")

    # 构建 RAG 向量索引
    if not is_index_ready():
        db = SessionLocal()
        all_pois = db.query(POI).all()
        poi_list = [
            {
                "id": p.id, "city": p.city, "name": p.name, "category": p.category,
                "lat": p.lat, "lng": p.lng, "address": p.address,
                "cost": p.cost, "duration": p.duration, "note": p.note,
                "rating": p.rating,
            }
            for p in all_pois
        ]
        db.close()
        if poi_list:
            build_index_from_pois(poi_list)
            logger.info(f"RAG 索引构建完成：{len(poi_list)} 个景点")

    logger.info("TripCraft 启动完成")
    yield
    # 关闭
    logger.info("TripCraft 关闭")


app = FastAPI(title="TripCraft API", version="2.0.0", lifespan=lifespan)

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
app.include_router(generate_stream.router)
app.include_router(verify.router)
app.include_router(feedback.router)
app.include_router(pois.router)
app.include_router(chat.router)
app.include_router(itineraries.router)
app.include_router(share.router)
app.include_router(weather.router)
app.include_router(packing.router)
app.include_router(auth.router)
app.include_router(pois_detail.router)
app.include_router(user.router)

# 注册异常处理
app.add_exception_handler(TripCraftError, trip_error_handler)


@app.get("/")
def root():
    return {"name": "TripCraft API", "version": "2.0.0", "docs": "/docs"}