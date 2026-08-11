# TripCraft MongoDB 改造方案

> MySQL 存关系型数据（用户/行程/POI/收藏），MongoDB 存长文本内容（帖子/评论）。

---

## 一、架构设计

### 数据库分工

```
┌─────────────────────────────────────────┐
│              后端 API                     │
│         FastAPI + SQLAlchemy             │
├──────────────────┬──────────────────────┤
│   MySQL           │   MongoDB            │
│   ─────────       │   ──────────         │
│   users           │   posts_content      │
│   pois            │   post_comments      │
│   saved_trips     │                      │
│   favorites       │                      │
│   reviews         │                      │
│   posts (元数据)   │                      │
│   post_likes      │                      │
│   ...             │                      │
└──────────────────┴──────────────────────┘
```

### 为什么这样拆

| 数据类型 | 存哪里 | 原因 |
|---|---|---|
| 帖子元数据（标题/城市/标签/计数） | MySQL | 需要关联查询（作者信息）、索引排序 |
| 帖子正文（Markdown 长文本） | MongoDB | 几千字 Markdown，文档型存储 |
| 行程 JSON（明信片渲染数据） | MongoDB | 大 JSON 文档，嵌套结构 |
| 评论 | MongoDB | 文档型，需要全文搜索 |
| 用户/行程/POI/收藏 | MySQL | 关系型，需要 JOIN 和事务 |

---

## 二、MongoDB 集合设计

### 2.1 posts_content 集合

存储帖子的正文内容和行程数据。

```javascript
// 文档结构
{
  _id: ObjectId("..."),          // MongoDB 自动生成
  post_id: 1,                    // 对应 MySQL posts.id（索引）
  content: "# 3天杭州美食之旅\n\n## Day 1...",  // 完整 Markdown 正文
  trip_json: {                   // 行程 JSON（用于明信片渲染）
    "destination": "杭州",
    "days": 3,
    "itinerary": [...],
    "total_cost": 440,
    "summary": "..."
  },
  created_at: ISODate("2026-08-11T..."),
  updated_at: ISODate("2026-08-11T..."),
  
  // 全文搜索索引字段
  search_text: "3天杭州美食之旅 西湖 灵隐寺 楼外楼...",  // 从标题+正文提取的纯文本
  
  // 标签数组（便于 MongoDB 内查询）
  tags: ["攻略", "美食"],
  city: "杭州"
}

// 索引
db.posts_content.createIndex({ post_id: 1 }, { unique: true })
db.posts_content.createIndex({ city: 1 })
db.posts_content.createIndex({ tags: 1 })
db.posts_content.createIndex({ search_text: "text" }, { default_language: "none" })  // 全文索引
```

### 2.2 post_comments 集合

存储评论内容。

```javascript
// 文档结构
{
  _id: ObjectId("..."),
  post_id: 1,                    // 对应 MySQL posts.id
  user_id: 3,                    // 评论者 ID
  user_nickname: "weric",        // 冗余存储，避免每次 JOIN
  content: "这个攻略太实用了！西湖醋鱼真的必吃！",  // 评论内容
  created_at: ISODate("2026-08-11T..."),
  
  // MongoDB 内嵌回复（如果以后要支持评论回复）
  replies: []                    // 预留
}

// 索引
db.post_comments.createIndex({ post_id: 1, created_at: -1 })  // 按帖子查评论，时间倒序
db.post_comments.createIndex({ user_id: 1 })                   // 按用户查评论
```

---

## 三、MySQL 表改造

### posts 表精简

```sql
-- 删除长文本字段
ALTER TABLE posts DROP COLUMN content;
ALTER TABLE posts DROP COLUMN trip_json;

-- 保留元数据
-- posts 表最终结构：
-- id, user_id, title, cover_image, city, tags, trip_id,
-- view_count, like_count, comment_count, created_at, updated_at
```

### post_comments 表删除

```sql
-- 评论迁移到 MongoDB，删除 MySQL 中的 post_comments 表
DROP TABLE post_comments;
```

---

## 四、后端代码改造

### 4.1 MongoDB 连接

**文件**：`backend/utils/mongo_client.py`

```python
"""MongoDB 客户端"""

from pymongo import MongoClient
from config import settings
from utils.logger import logger

_client = None


def get_mongo():
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_url)
        logger.info("MongoDB 连接成功")
    return _client


def get_db():
    """获取 TripCraft 数据库"""
    return get_mongo()[settings.mongo_db]


def get_posts_content():
    """获取帖子内容集合"""
    return get_db()["posts_content"]


def get_comments():
    """获取评论集合"""
    return get_db()["post_comments"]
```

### 4.2 配置更新

**文件**：`backend/config.py`

```python
class Settings(BaseSettings):
    # ... 现有配置 ...

    # MongoDB
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "tripcraft"
```

### 4.3 社区 API 改造

**文件**：`backend/api/community.py`

```python
# 帖子列表 — 只查 MySQL（元数据）
@router.get("/api/posts")
async def list_posts(page: int = 1, tag: str = "", city: str = "", db: Session = Depends(get_db)):
    query = db.query(Post)
    if tag:
        query = query.filter(Post.tags.contains(tag))
    if city:
        query = query.filter(Post.city == city)
    posts = query.order_by(Post.created_at.desc()).offset((page-1)*10).limit(10).all()
    # ... 返回元数据列表 ...

# 帖子详情 — MySQL 查元数据 + MongoDB 查正文
@router.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    # 1. MySQL 查元数据
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return {"error": "帖子不存在"}

    # 2. MongoDB 查正文
    from utils.mongo_client import get_posts_content
    content_doc = get_posts_content().find_one({"post_id": post_id})

    # 3. 合并返回
    return {
        "id": post.id,
        "title": post.title,
        "content": content_doc.get("content", "") if content_doc else "",
        "trip_json": content_doc.get("trip_json") if content_doc else None,
        "city": post.city,
        "tags": post.tags,
        # ... 其他元数据 ...
    }

# 发帖 — MySQL 存元数据 + MongoDB 存正文
@router.post("/api/posts")
async def create_post(req: CreatePostRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
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
    from utils.mongo_client import get_posts_content
    get_posts_content().insert_one({
        "post_id": post.id,
        "content": req.content,
        "trip_json": json.loads(req.trip_json) if req.trip_json else None,
        "search_text": req.title + " " + re.sub(r'[#*\-`>]', '', req.content)[:500],
        "tags": req.tags.split(",") if req.tags else [],
        "city": req.city,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })

    return {"status": "ok", "id": post.id}

# 评论 — 完全用 MongoDB
@router.get("/api/posts/{post_id}/comments")
async def list_comments(post_id: int, db: Session = Depends(get_db)):
    from utils.mongo_client import get_comments
    comments = get_comments().find({"post_id": post_id}).sort("created_at", -1)
    return [
        {
            "id": str(c["_id"]),
            "content": c["content"],
            "user_nickname": c.get("user_nickname", "未知"),
            "created_at": c["created_at"].strftime("%Y-%m-%d %H:%M"),
        }
        for c in comments
    ]

@router.post("/api/posts/{post_id}/comments")
async def create_comment(post_id: int, req: CreateCommentRequest, user: dict = Depends(require_user), db: Session = Depends(get_db)):
    # 查用户昵称
    user_record = db.query(User).filter(User.id == user["user_id"]).first()

    from utils.mongo_client import get_comments
    result = get_comments().insert_one({
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

# 全文搜索 — MongoDB text index
@router.get("/api/posts/search")
async def search_posts(q: str = Query(...)):
    from utils.mongo_client import get_posts_content
    results = get_posts_content().find(
        {"$text": {"$search": q}},
        {"score": {"$meta": "textScore"}, "post_id": 1}
    ).sort([("score", {"$meta": "textScore"})]).limit(20)

    post_ids = [r["post_id"] for r in results]
    # 再从 MySQL 查元数据
    # ...
```

### 4.4 数据迁移脚本

**文件**：`backend/scripts/migrate_posts_to_mongo.py`

```python
"""将 MySQL 中的帖子内容和评论迁移到 MongoDB"""

from database.models import SessionLocal, Post, PostComment, User
from utils.mongo_client import get_posts_content, get_comments
from utils.logger import logger
import json
from datetime import datetime

def migrate():
    db = SessionLocal()

    # 1. 迁移帖子内容
    posts = db.query(Post).all()
    for post in posts:
        if not post.content:
            continue
        get_posts_content().update_one(
            {"post_id": post.id},
            {"$set": {
                "post_id": post.id,
                "content": post.content,
                "trip_json": json.loads(post.trip_json) if post.trip_json else None,
                "search_text": post.title + " " + post.content[:500],
                "tags": post.tags.split(",") if post.tags else [],
                "city": post.city or "",
                "created_at": post.created_at or datetime.utcnow(),
                "updated_at": post.updated_at or datetime.utcnow(),
            }},
            upsert=True
        )
    logger.info(f"迁移 {len(posts)} 条帖子内容到 MongoDB")

    # 2. 迁移评论
    comments = db.query(PostComment).all()
    for comment in comments:
        user = db.query(User).filter(User.id == comment.user_id).first()
        get_comments().insert_one({
            "post_id": comment.post_id,
            "user_id": comment.user_id,
            "user_nickname": user.nickname if user else "未知",
            "content": comment.content,
            "created_at": comment.created_at or datetime.utcnow(),
        })
    logger.info(f"迁移 {len(comments)} 条评论到 MongoDB")

    db.close()

if __name__ == "__main__":
    migrate()
```

---

## 五、安装与配置

### 5.1 安装 MongoDB

```bash
# Mac
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community

# 验证
mongosh --eval "db.runCommand({ ping: 1 })"
```

### 5.2 安装 Python 驱动

```bash
pip install pymongo
```

### 5.3 创建索引

```bash
mongosh tripcraft
```

```javascript
db.posts_content.createIndex({ post_id: 1 }, { unique: true })
db.posts_content.createIndex({ city: 1 })
db.posts_content.createIndex({ tags: 1 })
db.posts_content.createIndex({ search_text: "text" })

db.post_comments.createIndex({ post_id: 1, created_at: -1 })
db.post_comments.createIndex({ user_id: 1 })
```

---

## 六、改造清单

| 步骤 | 内容 | 工作量 |
|---|---|---|
| 1 | 安装 MongoDB + pymongo | 0.5h |
| 2 | 创建 `utils/mongo_client.py` | 0.5h |
| 3 | 更新 `config.py` 添加 MongoDB 配置 | 0.1h |
| 4 | 改造 `api/community.py` — 帖子 CRUD | 2h |
| 5 | 改造 `api/community.py` — 评论 CRUD | 1h |
| 6 | 新增全文搜索 API | 1h |
| 7 | 数据迁移脚本 | 0.5h |
| 8 | MySQL 表改造（删除 content/trip_json 字段） | 0.5h |
| 9 | 测试验证 | 1h |
| **总计** | | **7.5h** |

---

## 七、验收标准

- [ ] MongoDB 连接成功，集合和索引创建
- [ ] 发帖时元数据存 MySQL，正文存 MongoDB
- [ ] 帖子详情页正确从两个数据库合并数据
- [ ] 评论完全用 MongoDB 存储
- [ ] 全文搜索能按关键词搜到帖子
- [ ] 数据迁移脚本执行成功，无数据丢失
- [ ] MySQL 中 content 和 trip_json 字段已删除