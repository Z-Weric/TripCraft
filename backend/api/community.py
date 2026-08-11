"""社区 API — MySQL 存元数据 + MongoDB 存正文和评论"""

import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database.models import get_db, Post, PostComment, PostLike, User
from utils.auth import get_current_user, require_user
from utils.mongo_client import get_posts_content, get_comments_collection
from utils.logger import logger

router = APIRouter()


class CreatePostRequest(BaseModel):
    title: str
    content: str
    city: str = ""
    tags: str = ""
    trip_id: Optional[int] = None
    trip_json: Optional[str] = None


class CreateCommentRequest(BaseModel):
    content: str


def _extract_search_text(title: str, content: str) -> str:
    """从标题和正文中提取纯文本用于全文搜索"""
    text = title + " " + content
    text = re.sub(r'[#*`\->\[\]()!]', ' ', text)
    return text[:1000]


# ===== 帖子列表（只查 MySQL 元数据）=====

@router.get("/api/posts")
async def list_posts(
    page: int = Query(1, ge=1),
    tag: str = Query(""),
    city: str = Query(""),
    db: Session = Depends(get_db),
):
    """帖子列表 — 只查 MySQL 元数据"""
    query = db.query(Post)
    if tag:
        query = query.filter(Post.tags.contains(tag))
    if city:
        query = query.filter(Post.city == city)

    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset((page - 1) * 10).limit(10).all()

    result = []
    for p in posts:
        author = db.query(User).filter(User.id == p.user_id).first()
        result.append({
            "id": p.id,
            "title": p.title,
            "city": p.city,
            "tags": p.tags,
            "cover_image": p.cover_image,
            "view_count": p.view_count,
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "created_at": p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
            "author": {
                "id": author.id if author else 0,
                "nickname": author.nickname if author else "未知",
            } if author else {"id": 0, "nickname": "未知"},
        })

    return {"posts": result, "total": total, "page": page, "pages": (total + 9) // 10}


# ===== 帖子详情（MySQL 元数据 + MongoDB 正文）=====

@router.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """帖子详情 — MySQL 查元数据 + MongoDB 查正文"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return {"error": "帖子不存在"}

    # 增加浏览量
    post.view_count = (post.view_count or 0) + 1
    db.commit()

    author = db.query(User).filter(User.id == post.user_id).first()

    # MongoDB 查正文
    content_doc = None
    posts_col = get_posts_content()
    if posts_col is not None:
        content_doc = posts_col.find_one({"post_id": post_id})

    return {
        "id": post.id,
        "title": post.title,
        "content": content_doc.get("content", "") if content_doc else "",
        "city": post.city,
        "tags": post.tags,
        "trip_json": content_doc.get("trip_json") if content_doc else None,
        "view_count": post.view_count,
        "like_count": post.like_count,
        "comment_count": post.comment_count,
        "created_at": post.created_at.strftime("%Y-%m-%d %H:%M") if post.created_at else "",
        "author": {
            "id": author.id if author else 0,
            "nickname": author.nickname if author else "未知",
            "avatar": author.avatar if author else "",
        } if author else {"id": 0, "nickname": "未知", "avatar": ""},
    }


# ===== 发帖（MySQL 存元数据 + MongoDB 存正文）=====

@router.post("/api/posts")
async def create_post(req: CreatePostRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """发帖 — 元数据存 MySQL，正文存 MongoDB"""
    # 1. MySQL 存元数据
    post = Post(
        user_id=user["user_id"],
        title=req.title,
        city=req.city,
        tags=req.tags,
        trip_id=req.trip_id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # 2. MongoDB 存正文
    trip_json_obj = None
    if req.trip_json:
        try:
            trip_json_obj = json.loads(req.trip_json)
        except json.JSONDecodeError:
            trip_json_obj = None

    posts_col = get_posts_content()
    if posts_col is not None:
        posts_col.insert_one({
            "post_id": post.id,
            "content": req.content,
            "trip_json": trip_json_obj,
            "search_text": _extract_search_text(req.title, req.content),
            "tags": req.tags.split(",") if req.tags else [],
            "city": req.city,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        })

    logger.info(f"帖子发布: id={post.id}, user={user['user_id']}, title={req.title}")
    return {"status": "ok", "id": post.id}


# ===== 删除帖（MySQL + MongoDB 都删）=====

@router.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """删除帖子 — 同时删 MySQL 和 MongoDB"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return {"error": "帖子不存在"}
    if post.user_id != user["user_id"]:
        return {"error": "无权操作"}

    # 删 MongoDB 正文
    posts_col = get_posts_content()
    if posts_col is not None:
        posts_col.delete_one({"post_id": post_id})

    # 删 MongoDB 评论
    comments_col = get_comments_collection()
    if comments_col is not None:
        comments_col.delete_many({"post_id": post_id})

    # 删 MySQL 点赞
    db.query(PostLike).filter(PostLike.post_id == post_id).delete()

    # 删 MySQL 帖子元数据
    db.delete(post)
    db.commit()
    logger.info(f"帖子删除: id={post_id}")
    return {"status": "ok"}


# ===== 点赞（MySQL）=====

@router.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """点赞"""
    existing = db.query(PostLike).filter(PostLike.user_id == user["user_id"], PostLike.post_id == post_id).first()
    if existing:
        return {"status": "ok", "liked": True}

    db.add(PostLike(user_id=user["user_id"], post_id=post_id))
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.like_count = (post.like_count or 0) + 1
    db.commit()
    return {"status": "ok", "liked": True}


@router.delete("/api/posts/{post_id}/like")
async def unlike_post(post_id: int, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """取消点赞"""
    like = db.query(PostLike).filter(PostLike.user_id == user["user_id"], PostLike.post_id == post_id).first()
    if like:
        db.delete(like)
        post = db.query(Post).filter(Post.id == post_id).first()
        if post and post.like_count > 0:
            post.like_count -= 1
        db.commit()
    return {"status": "ok", "liked": False}


# ===== 评论（完全用 MongoDB）=====

@router.get("/api/posts/{post_id}/comments")
async def list_comments(post_id: int, db: Session = Depends(get_db)):
    """评论列表 — MongoDB"""
    comments_col = get_comments_collection()
    if comments_col is None:
        return []

    comments = comments_col.find({"post_id": post_id}).sort("created_at", -1)
    result = []
    for c in comments:
        result.append({
            "id": str(c["_id"]),
            "content": c["content"],
            "user_nickname": c.get("user_nickname", "未知"),
            "created_at": c["created_at"].strftime("%Y-%m-%d %H:%M") if c.get("created_at") else "",
        })
    return result


@router.post("/api/posts/{post_id}/comments")
async def create_comment(post_id: int, req: CreateCommentRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """发评论 — MongoDB"""
    user_record = db.query(User).filter(User.id == user["user_id"]).first()

    comments_col = get_comments_collection()
    if comments_col is None:
        return {"error": "评论服务不可用"}

    result = comments_col.insert_one({
        "post_id": post_id,
        "user_id": user["user_id"],
        "user_nickname": user_record.nickname if user_record else "未知",
        "content": req.content,
        "created_at": datetime.utcnow(),
    })

    # MySQL 更新评论计数
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.comment_count = (post.comment_count or 0) + 1
        db.commit()

    return {"status": "ok", "id": str(result.inserted_id)}


@router.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: str, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """删除评论 — MongoDB"""
    from bson import ObjectId
    comments_col = get_comments_collection()
    if comments_col is None:
        return {"error": "评论服务不可用"}

    try:
        oid = ObjectId(comment_id)
    except Exception:
        return {"error": "评论 ID 无效"}

    comment = comments_col.find_one({"_id": oid})
    if not comment:
        return {"error": "评论不存在"}
    if comment["user_id"] != user["user_id"]:
        return {"error": "无权操作"}

    comments_col.delete_one({"_id": oid})

    # MySQL 更新评论计数
    post = db.query(Post).filter(Post.id == comment["post_id"]).first()
    if post and post.comment_count > 0:
        post.comment_count -= 1
        db.commit()

    return {"status": "ok"}


# ===== 全文搜索（MongoDB text index）=====

@router.get("/api/posts/search")
async def search_posts(q: str = Query(..., description="搜索关键词"), db: Session = Depends(get_db)):
    """全文搜索 — MongoDB text index"""
    posts_col = get_posts_content()
    if posts_col is None:
        return {"posts": [], "total": 0}

    # MongoDB 全文搜索
    results = posts_col.find(
        {"$text": {"$search": q}},
        {"score": {"$meta": "textScore"}, "post_id": 1}
    ).sort([("score", {"$meta": "textScore"})]).limit(20)

    post_ids = [r["post_id"] for r in results]
    if not post_ids:
        return {"posts": [], "total": 0}

    # 从 MySQL 查元数据
    posts = db.query(Post).filter(Post.id.in_(post_ids)).all()
    result = []
    for p in posts:
        author = db.query(User).filter(User.id == p.user_id).first()
        result.append({
            "id": p.id,
            "title": p.title,
            "city": p.city,
            "tags": p.tags,
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "created_at": p.created_at.strftime("%Y-%m-%d") if p.created_at else "",
            "author": {"id": author.id if author else 0, "nickname": author.nickname if author else "未知"} if author else {"id": 0, "nickname": "未知"},
        })

    return {"posts": result, "total": len(result)}