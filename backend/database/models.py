"""SQLite 数据模型 — 景点数据库 + 用户反馈 + 行程持久化 (v2)"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Index, event
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from config import settings
from utils.logger import logger

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tripcraft.db")
DB_PATH = os.path.abspath(DB_PATH)

# 确保数据目录存在
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(
    settings.database_url.replace("sqlite:///data/", f"sqlite:///{DB_PATH}") if settings.database_url.startswith("sqlite") else settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# SQLite WAL 模式 + 性能优化
if "sqlite" in settings.database_url:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class POI(Base):
    """景点 POI 数据"""
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), index=True)  # 添加索引
    lat = Column(Float)
    lng = Column(Float)
    address = Column(String(255))
    cost = Column(Integer, default=0)
    duration = Column(String(20))
    note = Column(Text)
    rating = Column(Float, default=0)

    __table_args__ = (
        Index("idx_poi_city_category", "city", "category"),
    )


class Feedback(Base):
    """用户反馈"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    destination = Column(String(50))
    days = Column(Integer)
    budget = Column(Integer)
    preferences = Column(String(255))
    feedback_type = Column(String(20))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class SavedTrip(Base):
    """保存的行程"""
    __tablename__ = "saved_trips"

    id = Column(Integer, primary_key=True, autoincrement=True)
    destination = Column(String(50), nullable=False, index=True)
    days = Column(Integer)
    budget = Column(Integer)
    preferences = Column(String(255))
    summary = Column(String(255))
    total_cost = Column(Integer)
    itinerary_json = Column(Text, nullable=False)  # 完整行程 JSON
    verification_json = Column(Text)               # 验证结果 JSON
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """初始化数据库 + 写入种子景点数据"""
    Base.metadata.create_all(engine)

    from .seed_data import SEED_POIS
    db = SessionLocal()
    if db.query(POI).count() == 0:
        for poi in SEED_POIS:
            db.add(POI(**poi))
        db.commit()
        logger.info(f"已写入 {len(SEED_POIS)} 条种子景点数据")
    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()