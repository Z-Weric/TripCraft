"""用户相关 API — 统计 + 偏好 + 评论历史"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models import get_db, SavedTrip, Favorite, Review, POI
from utils.auth import require_user
from utils.logger import logger

router = APIRouter()


@router.get("/api/user/stats")
async def user_stats(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """用户旅行统计"""
    user_id = user["user_id"]

    # 行程统计
    trips = db.query(SavedTrip).filter(SavedTrip.user_id == user_id).all()
    trip_count = len(trips)
    total_days = sum(t.days or 0 for t in trips)
    total_cost = sum(t.total_cost or 0 for t in trips)
    cities = set(t.destination for t in trips if t.destination)
    city_count = len(cities)

    # 收藏数
    fav_count = db.query(Favorite).filter(Favorite.user_id == user_id).count()

    # 评论数
    review_count = db.query(Review).filter(Review.user_id == user_id).count()

    logger.info(f"用户统计: user={user_id}, trips={trip_count}, cities={city_count}")

    return {
        "trip_count": trip_count,
        "total_days": total_days,
        "city_count": city_count,
        "total_cost": total_cost,
        "favorite_count": fav_count,
        "review_count": review_count,
        "cities": list(cities),
    }


@router.get("/api/user/reviews")
async def user_reviews(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """用户评论历史"""
    user_id = user["user_id"]
    reviews = db.query(Review, POI).join(POI, Review.poi_id == POI.id).filter(Review.user_id == user_id).all()

    return [
        {
            "id": r.id,
            "poi_id": r.poi_id,
            "poi_name": p.name,
            "city": p.city,
            "category": p.category,
            "rating": r.rating,
            "comment": r.comment or "",
            "created_at": r.created_at.strftime("%Y-%m-%d") if r.created_at else "",
        }
        for r, p in reviews
    ]


@router.get("/api/user/cities")
async def user_cities(db: Session = Depends(get_db), user: dict = Depends(require_user)):
    """用户去过的城市列表 + 行程数 + 坐标"""
    user_id = user["user_id"]

    # 内置城市坐标
    CITY_COORDS = {
        "杭州": (30.2741, 120.1551), "成都": (30.5728, 104.0668),
        "西安": (34.3416, 108.9398), "厦门": (24.4798, 118.0894),
        "苏州": (31.2989, 120.5853), "南京": (32.0603, 118.7969),
        "重庆": (29.5630, 106.5516), "长沙": (28.2282, 112.9388),
        "青岛": (36.0671, 120.3826), "大理": (25.6065, 100.2670),
    }

    results = db.query(
        SavedTrip.destination,
        func.count(SavedTrip.id).label("count"),
        func.sum(SavedTrip.total_cost).label("total_cost"),
    ).filter(SavedTrip.user_id == user_id).group_by(SavedTrip.destination).all()

    cities = []
    for dest, count, cost in results:
        coords = CITY_COORDS.get(dest, (0, 0))
        cities.append({
            "city": dest,
            "trip_count": count,
            "total_cost": cost or 0,
            "lat": coords[0],
            "lng": coords[1],
        })

    return cities