"""社区 API — 帖子 CRUD + 评论 + 点赞"""

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import get_db, Post, PostComment, PostLike, User
from utils.auth import get_current_user, require_user
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


@router.get("/api/posts")
async def list_posts(
    page: int = Query(1, ge=1),
    tag: str = Query(""),
    city: str = Query(""),
    db: Session = Depends(get_db),
):
    """帖子列表（分页 10 条/页）"""
    query = db.query(Post)
    if tag:
        query = query.filter(Post.tags.contains(tag))
    if city:
        query = query.filter(Post.city == city)

    total = query.count()
    posts = query.order_by(Post.created_at.desc()).offset((page - 1) * 10).limit(10).all()

    # 查作者信息
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


@router.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """帖子详情"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return {"error": "帖子不存在"}

    # 增加浏览量
    post.view_count = (post.view_count or 0) + 1
    db.commit()

    author = db.query(User).filter(User.id == post.user_id).first()

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "city": post.city,
        "tags": post.tags,
        "trip_json": post.trip_json,
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


@router.post("/api/posts")
async def create_post(req: CreatePostRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """发布帖子"""
    post = Post(
        user_id=user["user_id"],
        title=req.title,
        content=req.content,
        city=req.city,
        tags=req.tags,
        trip_id=req.trip_id,
        trip_json=req.trip_json,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    logger.info(f"帖子发布: id={post.id}, user={user['user_id']}, title={req.title}")
    return {"status": "ok", "id": post.id}


@router.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """删除帖子（仅作者）"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return {"error": "帖子不存在"}
    if post.user_id != user["user_id"]:
        return {"error": "无权操作"}

    # 删除关联评论和点赞
    db.query(PostComment).filter(PostComment.post_id == post_id).delete()
    db.query(PostLike).filter(PostLike.post_id == post_id).delete()
    db.delete(post)
    db.commit()
    logger.info(f"帖子删除: id={post_id}")
    return {"status": "ok"}


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


@router.get("/api/posts/{post_id}/comments")
async def list_comments(post_id: int, db: Session = Depends(get_db)):
    """评论列表"""
    comments = db.query(PostComment).filter(PostComment.post_id == post_id).order_by(PostComment.created_at.desc()).all()
    result = []
    for c in comments:
        author = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "content": c.content,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "",
            "author": {
                "id": author.id if author else 0,
                "nickname": author.nickname if author else "未知",
            } if author else {"id": 0, "nickname": "未知"},
        })
    return result


@router.post("/api/posts/{post_id}/comments")
async def create_comment(post_id: int, req: CreateCommentRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """发评论"""
    comment = PostComment(
        post_id=post_id,
        user_id=user["user_id"],
        content=req.content,
    )
    db.add(comment)
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.comment_count = (post.comment_count or 0) + 1
    db.commit()
    db.refresh(comment)
    return {"status": "ok", "id": comment.id}


@router.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: int, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    """删除评论（仅作者）"""
    comment = db.query(PostComment).filter(PostComment.id == comment_id).first()
    if not comment:
        return {"error": "评论不存在"}
    if comment.user_id != user["user_id"]:
        return {"error": "无权操作"}

    post = db.query(Post).filter(Post.id == comment.post_id).first()
    if post and post.comment_count > 0:
        post.comment_count -= 1

    db.delete(comment)
    db.commit()
    return {"status": "ok"}