"""景点详情 + 收藏 + 评论 API"""

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import get_db, POI, Favorite, Review
from utils.auth import get_current_user, require_user
from utils.logger import logger

router = APIRouter()


class ReviewRequest(BaseModel):
    rating: int  # 1-5
    comment: str = ""


@router.get("/api/pois/{poi_id}/detail")
async def get_poi_detail(poi_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """景点完整信息 + 用户评分统计 + 是否已收藏"""
    poi = db.query(POI).filter(POI.id == poi_id).first()
    if not poi:
        return {"error": "景点不存在"}

    # 用户评分统计
    reviews = db.query(Review).filter(Review.poi_id == poi_id).all()
    user_rating_avg = db.query(func.avg(Review.rating)).filter(Review.poi_id == poi_id).scalar() or 0
    review_count = len(reviews)

    # 综合评分动态权重
    if review_count < 10:
        composite = poi.rating * 0.8 + float(user_rating_avg) * 0.2
    else:
        composite = poi.rating * 0.4 + float(user_rating_avg) * 0.6

    # 是否已收藏
    is_favorited = False
    user = await get_current_user(authorization)
    if user:
        fav = db.query(Favorite).filter(Favorite.user_id == user["user_id"], Favorite.poi_id == poi_id).first()
        is_favorited = fav is not None

    # 前 3 条评论
    recent_reviews = []
    for r in reviews[:3]:
        recent_reviews.append({
            "id": r.id,
            "rating": r.rating,
            "comment": r.comment or "",
            "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
        })

    return {
        "id": poi.id,
        "name": poi.name,
        "category": poi.category,
        "city": poi.city,
        "lat": poi.lat,
        "lng": poi.lng,
        "address": poi.address,
        "cost": poi.cost,
        "duration": poi.duration,
        "note": poi.note,
        "amap_rating": poi.rating,
        "user_rating_avg": round(float(user_rating_avg), 1),
        "review_count": review_count,
        "composite_rating": round(composite, 1),
        "is_favorited": is_favorited,
        "reviews": recent_reviews,
    }


@router.post("/api/pois/{poi_id}/favorite")
async def add_favorite(poi_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """收藏景点"""
    existing = db.query(Favorite).filter(Favorite.user_id == user["user_id"], Favorite.poi_id == poi_id).first()
    if existing:
        return {"status": "ok", "favorited": True}

    db.add(Favorite(user_id=user["user_id"], poi_id=poi_id))
    db.commit()
    logger.info(f"收藏景点: user={user['user_id']}, poi={poi_id}")
    return {"status": "ok", "favorited": True}


@router.delete("/api/pois/{poi_id}/favorite")
async def remove_favorite(poi_id: int, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """取消收藏"""
    fav = db.query(Favorite).filter(Favorite.user_id == user["user_id"], Favorite.poi_id == poi_id).first()
    if fav:
        db.delete(fav)
        db.commit()
        logger.info(f"取消收藏: user={user['user_id']}, poi={poi_id}")
    return {"status": "ok", "favorited": False}


@router.get("/api/favorites")
async def list_favorites(city: Optional[str] = Query(None), db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """当前用户收藏列表"""
    query = db.query(POI).join(Favorite, Favorite.poi_id == POI.id).filter(Favorite.user_id == user["user_id"])
    if city:
        query = query.filter(POI.city == city)
    pois = query.all()
    return [
        {
            "id": p.id, "name": p.name, "category": p.category, "city": p.city,
            "lat": p.lat, "lng": p.lng, "address": p.address, "cost": p.cost,
            "duration": p.duration, "rating": p.rating,
        }
        for p in pois
    ]


@router.get("/api/favorites/ids")
async def favorite_ids(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """收藏 ID 列表（前端标记用）"""
    favs = db.query(Favorite.poi_id).filter(Favorite.user_id == user["user_id"]).all()
    return [f[0] for f in favs]


@router.post("/api/pois/{poi_id}/review")
async def add_review(poi_id: int, req: ReviewRequest, db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """提交评分评论（每人每景点一次）"""
    existing = db.query(Review).filter(Review.user_id == user["user_id"], Review.poi_id == poi_id).first()
    if existing:
        existing.rating = max(1, min(5, req.rating))
        existing.comment = req.comment
        db.commit()
        return {"status": "ok"}

    review = Review(
        user_id=user["user_id"],
        poi_id=poi_id,
        rating=max(1, min(5, req.rating)),
        comment=req.comment,
    )
    db.add(review)
    db.commit()
    logger.info(f"评论景点: user={user['user_id']}, poi={poi_id}, rating={req.rating}")
    return {"status": "ok"}


@router.get("/api/pois/{poi_id}/reviews")
async def list_reviews(poi_id: int, db: Session = Depends(get_db)):
    """景点评论列表"""
    reviews = db.query(Review).filter(Review.poi_id == poi_id).order_by(Review.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "rating": r.rating,
            "comment": r.comment or "",
            "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
        }
        for r in reviews
    ]