"""SQLite 数据模型 — 景点数据库 + 用户反馈"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tripcraft.db")
DB_PATH = os.path.abspath(DB_PATH)

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class POI(Base):
    """景点 POI 数据"""
    __tablename__ = "pois"

    id = Column(Integer, primary_key=True, autoincrement=True)
    city = Column(String(50), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50))  # 自然风光/美食/历史文化/购物
    lat = Column(Float)
    lng = Column(Float)
    address = Column(String(255))
    cost = Column(Integer, default=0)  # 平均花费
    duration = Column(String(20))  # 建议游玩时长
    note = Column(Text)
    rating = Column(Float, default=0)


class Feedback(Base):
    """用户反馈"""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    destination = Column(String(50))
    days = Column(Integer)
    budget = Column(Integer)
    preferences = Column(String(255))
    feedback_type = Column(String(20))  # useful / improve
    comment = Column(Text)
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
        print(f"已写入 {len(SEED_POIS)} 条种子景点数据")
    db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()