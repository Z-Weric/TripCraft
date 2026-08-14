"""数据模型 — 景点数据库 + 用户反馈 + 行程持久化 (v2 MySQL)"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Index, event, inspect, text
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
    model_version = Column(String(100), default="none")
    planner_version = Column(String(50), default="planner-v1")
    poi_version = Column(String(64), nullable=True)
    generation_source = Column(String(30), default="planner")
    validation_status = Column(String(30), default="fallback")
    fallback_reason = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TripEditEvent(Base):
    """Structured difference between consecutive saved itinerary versions."""
    __tablename__ = "trip_edit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    from_version = Column(Integer, nullable=False)
    to_version = Column(Integer, nullable=False)
    action_types = Column(String(255), nullable=False)
    diff_json = Column(Text, nullable=False)
    before_hash = Column(String(64), nullable=False)
    after_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ShareToken(Base):
    """Persistent, revocable token for read-only access to a saved trip."""
    __tablename__ = "share_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_by = Column(Integer, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


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


class Post(Base):
    """社区帖子"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)  # 正文存 MongoDB
    cover_image = Column(String(255), default="")
    city = Column(String(50), default="", index=True)
    tags = Column(String(255), default="")
    trip_id = Column(Integer, nullable=True)
    trip_json = Column(Text)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class PostComment(Base):
    """帖子评论"""
    __tablename__ = "post_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostLike(Base):
    """帖子点赞"""
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    post_id = Column(Integer, nullable=False)


class TripQualityLog(Base):
    """行程质量结构化记录 — 低评分或验证失败时写入，供训练数据筛选使用。

    design:
      - trigger: "low_rating" | "validation_failed"
      - reason_json: 结构化原因（验证错误码列表、生成来源、回退原因等）
      - 禁止把单条记录直接用于在线训练，仅供离线分析。
    """
    __tablename__ = "trip_quality_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trip_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    trigger = Column(String(30), nullable=False, index=True)
    destination = Column(String(50))
    days = Column(Integer)
    budget = Column(Integer)
    preferences = Column(String(255))
    generation_source = Column(String(30))
    validation_status = Column(String(30))
    fallback_reason = Column(Text, nullable=True)
    model_version = Column(String(100), default="none")
    error_codes = Column(String(500), nullable=True)
    reason_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """初始化数据库 + 写入种子景点数据"""
    Base.metadata.create_all(engine)
    _apply_additive_migrations()

    from .seed_data import SEED_POIS
    db = SessionLocal()
    if db.query(POI).count() == 0:
        for poi in SEED_POIS:
            db.add(POI(**poi))
        db.commit()
        logger.info(f"已写入 {len(SEED_POIS)} 条种子景点数据")
    db.close()


def _apply_additive_migrations() -> None:
    """Add newly introduced nullable/defaulted columns without rebuilding user tables."""
    migrations = {
        "saved_trips": {
            "model_version": "VARCHAR(100) DEFAULT 'none'",
            "planner_version": "VARCHAR(50) DEFAULT 'planner-v1'",
            "poi_version": "VARCHAR(64) NULL",
            "generation_source": "VARCHAR(30) DEFAULT 'planner'",
            "validation_status": "VARCHAR(30) DEFAULT 'fallback'",
            "fallback_reason": "TEXT NULL",
            "version": "INTEGER DEFAULT 1",
            "updated_at": "DATETIME NULL",
        },
        "trip_quality_logs": {
            "trip_id": "INTEGER NULL",
            "user_id": "INTEGER NULL",
            "trigger": "VARCHAR(30) NOT NULL",
            "destination": "VARCHAR(50) NULL",
            "days": "INTEGER NULL",
            "budget": "INTEGER NULL",
            "preferences": "VARCHAR(255) NULL",
            "generation_source": "VARCHAR(30) NULL",
            "validation_status": "VARCHAR(30) NULL",
            "fallback_reason": "TEXT NULL",
            "model_version": "VARCHAR(100) DEFAULT 'none'",
            "error_codes": "VARCHAR(500) NULL",
            "reason_json": "TEXT NOT NULL",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        },
    }
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table_name, columns in migrations.items():
            if table_name not in table_names:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name in existing:
                    continue
                connection.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
                )
                logger.info(f"数据库迁移完成: {table_name}.{column_name}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
