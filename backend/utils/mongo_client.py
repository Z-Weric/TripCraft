"""MongoDB 客户端 — 帖子正文 + 评论存储"""

from pymongo import MongoClient
from config import settings
from utils.logger import logger
from typing import Optional

_client: Optional[MongoClient] = None


def get_mongo() -> Optional[MongoClient]:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_url)
        try:
            _client.admin.command("ping")
            logger.info("MongoDB 连接成功")
        except Exception as e:
            logger.error(f"MongoDB 连接失败: {e}")
            _client = None
    return _client


def get_db():
    """获取 TripCraft 数据库"""
    client = get_mongo()
    if client is None:
        return None
    return client[settings.mongo_db]


def get_posts_content():
    """获取帖子内容集合"""
    db = get_db()
    if db is None:
        return None
    return db["posts_content"]


def get_comments_collection():
    """获取评论集合"""
    db = get_db()
    if db is None:
        return None
    return db["post_comments"]