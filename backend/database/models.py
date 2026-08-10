"""数据模型 — 景点数据库 + 用户反馈 + 行程持久化 (v2 MySQL)"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Index, event
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os
from config import settings
from utils.logger import logger

DB_URL = settings.database_url
IS_SQLITE = DB_URL.startswith("sqlite")

if IS_SQLITE:
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "tripcraft.db")
    DB_PATH = os.path.abspath(DB_PATH)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    DB_URL_RESOLVED = DB_URL.replace("sqlite:///data/", f"sqlite:///{DB_PATH}")
else:
    DB_URL_RESOLVED = DB_URL

engine = create_engine(
    DB_URL_RESOLVED,
    echo=False,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True if not IS_SQLITE else False,
    pool_size=10 if not IS_SQLITE else None,
    max_overflow=20 if not IS_SQLITE else None,
)

# SQLite WAL 模式 + 性能优化
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")
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
    category = Column(String(50), index=True)
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
    itinerary_json = Column(Text, nullable=False)
    verification_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True, index=True)
    is_public = Column(Integer, default=0)
    user_rating = Column(Integer, default=0)


class User(Base):
    """用户"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False)
    username = Column(String(50), unique=True)
    password_hash = Column(String(255))
    nickname = Column(String(50))
    avatar = Column(String(255), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.utcnow)


class VerificationCode(Base):
    """验证码"""
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Favorite(Base):
    """景点收藏"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    poi_id = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    """景点评论"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    poi_id = Column(Integer, nullable=False, index=True)
    rating = Column(Integer, default=5)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class TripLike(Base):
    """行程点赞"""
    __tablename__ = "trip_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    trip_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PreferenceTemplate(Base):
    """偏好模板"""
    __tablename__ = "preference_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    preferences_json = Column(Text, nullable=False)
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