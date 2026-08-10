# TripCraft v2.5 — 用户体系与个性化功能设计清单

> 基于 MySQL 数据库，新增用户体系、个性化功能和社交能力。
> 游客可用核心功能，登录后解锁个性化和社交能力。

---

## 〇、权限模型

| 功能 | 游客 | 已登录用户 |
|---|---|---|
| 生成行程 | ✅ | ✅ |
| 查看公开行程 | ✅ | ✅ |
| 查看景点详情 | ✅ | ✅ |
| 保存行程到历史 | ❌（仅本次会话） | ✅ |
| 收藏景点 | ❌ | ✅ |
| 评分评论 | ❌ | ✅ |
| 个人中心 | ❌ | ✅ |
| 编辑/删除行程 | ❌ | ✅（仅自己的） |

---

## 一、用户体系

### 1.1 用户登录（验证码方案，无密码）

**设计原则**：旅行工具是低频使用产品，用户不愿设置密码。用验证码登录降低门槛。

**后端**
- `users` 表：id, email, nickname, avatar, created_at, last_login_at
- `verification_codes` 表：id, email, code, expires_at, used
- `POST /api/auth/send-code` — 发送验证码到邮箱（SMTP），5 分钟有效，60 秒内不可重复发送
- `POST /api/auth/verify` — 验证码校验，通过则返回 JWT token（新用户自动注册）
- `GET /api/auth/me` — 获取当前用户信息
- `PUT /api/auth/profile` — 修改昵称/头像
- JWT 有效期 7 天，过期后重新发验证码登录
- 密码字段：无（验证码方案不需要）

**前端**
- 登录页面（路由 `/login`）：输入邮箱 → 发送验证码 → 输入验证码 → 登录
- 未登录时顶栏显示「登录」按钮
- 登录后顶栏显示头像 + 昵称 + 下拉菜单（我的行程 / 收藏 / 退出）
- token 存 localStorage，axios 请求头自动携带
- 游客生成行程时提示「登录后可保存行程」

### 1.2 个人中心

**后端**
- `GET /api/user/stats` — 用户统计（生成行程数、收藏景点数、评论数）
- `GET /api/user/profile` — 用户资料

**前端**
- 路由 `/profile`
- 展示：头像、昵称、注册时间、统计数据
- Tab 切换：我的行程 / 收藏景点 / 我的评论

---

## 二、行程归属

### 2.1 行程绑定用户

**后端**
- `saved_trips` 表新增 `user_id` 字段（NULL = 游客会话临时数据）
- `saved_trips` 表新增 `is_public` 字段（0 = 私有，1 = 公开）
- `POST /api/itineraries` — 已登录自动绑定 user_id，游客返回临时 ID 不入库
- `GET /api/itineraries` — 只返回当前用户的行程（需登录）
- `GET /api/itineraries/{id}` — owner 可看自己的，公开行程任何人可看
- `DELETE /api/itineraries/{id}` — 仅 owner 可删
- `PUT /api/itineraries/{id}/visibility` — 切换公开/私有（仅 owner）

**前端**
- 历史记录页面只显示自己的行程（未登录时引导登录）
- 行程详情页有「设为公开」开关
- 游客生成行程后弹窗「登录后可永久保存」

### 2.2 行程点赞

**后端**
- `trip_likes` 表：id, user_id, trip_id, created_at
- `POST /api/trips/{id}/like` — 点赞（需登录）
- `DELETE /api/trips/{id}/like` — 取消点赞
- `GET /api/trips/{id}/likes` — 点赞数 + 是否已点赞

**前端**
- 公开行程详情页显示点赞按钮 + 数量
- 未登录点击点赞 → 跳转登录

---

## 三、景点互动

### 3.1 景点收藏

**后端**
- `favorites` 表：id, user_id, poi_id, created_at, UNIQUE(user_id, poi_id)
- `POST /api/pois/{id}/favorite` — 收藏（需登录）
- `DELETE /api/pois/{id}/favorite` — 取消收藏
- `GET /api/favorites` — 当前用户收藏列表（分页，支持城市过滤）
- `GET /api/favorites/ids` — 收藏 ID 列表（前端用于标记已收藏状态）
- **算法增强**：生成行程时收藏的景点 score +1.0（可在 config 中配置权重）

**前端**
- 景点详情弹窗中显示收藏按钮（星标，已收藏高亮）
- 个人中心「收藏景点」Tab 展示收藏列表
- SearchBar 下方增加「优先收藏景点」复选框

### 3.2 景点评分评论

**后端**
- `reviews` 表：id, user_id, poi_id, rating(1-5), comment, created_at
- `POST /api/pois/{id}/review` — 提交评分评论（需登录，每人每景点一次）
- `GET /api/pois/{id}/reviews` — 景点评论列表（分页）
- `DELETE /api/reviews/{id}` — 删除自己的评论
- **综合评分动态权重**：
  ```
  用户评分数 < 10:  综合评分 = 高德评分 * 0.8 + 用户均分 * 0.2
  用户评分数 >= 10: 综合评分 = 高德评分 * 0.4 + 用户均分 * 0.6
  ```

**前端**
- 景点详情弹窗显示用户评论列表
- 登录用户可提交评分（5 星选择器）+ 文字评论
- 行程中景点旁显示用户评分标记（如有）

### 3.3 景点详情卡片

**后端**
- `GET /api/pois/{id}/detail` — 景点完整信息 + 用户评分统计 + 评论列表 + 是否已收藏

**前端**
- 点击行程中景点名展开详情弹窗
- 内容：地址、分类、高德评分、用户评分、门票、时长、备注
- 用户评论区域（前 3 条 + 「查看更多」）
- 收藏按钮 + 评分入口

---

## 四、个性化

### 4.1 偏好模板

**后端**
- `preference_templates` 表：id, user_id, name, preferences_json, created_at
- `POST /api/templates` — 保存偏好模板（需登录）
- `GET /api/templates` — 当前用户模板列表
- `DELETE /api/templates/{id}` — 删除（仅自己的）

**前端**
- SearchBar 下方显示「我的偏好模板」快捷按钮
- 点击模板一键填充偏好权重
- 生成行程后可「保存当前偏好为模板」

### 4.2 行程评价反馈算法

**后端**
- `saved_trips` 表新增 `user_rating` 字段（0=未评价, 1-5=评分）
- `PUT /api/itineraries/{id}/rate` — 给行程打分
- **算法反馈**：
  - 评分 1-2 星（差评）：记录偏好组合 + 入选景点列表，下次相同偏好生成时排除这些景点
  - 评分 4-5 星（好评）：该行程中的景点在相同偏好下 score +0.5
- `bad_trip_pois` 表：id, user_id, preferences_hash, poi_ids_json, created_at

**前端**
- 行程生成后弹出评分弹窗（「这次行程怎么样？」可跳过）
- 历史记录列表显示行程评分

---

## 五、社交发现

### 5.1 公开行程广场

**后端**
- `GET /api/discover` — 公开行程列表（按点赞数降序，分页 20 条/页）
- `GET /api/discover/hot` — 热门行程（近 7 天点赞最多，Top 10）
- **冷启动**：公开行程 < 20 条时不显示广场入口，显示「敬请期待」

**前端**
- 路由 `/discover`
- 卡片瀑布流：目的地图片、天数、总花费、点赞数、作者昵称
- 点击进入只读详情页（明信片 + 地图 + 花费，不可编辑）

### 5.2 城市热度排行

**后端**
- `GET /api/ranking/cities` — 城市被生成行程次数排序（基于 saved_trips 统计）
- `GET /api/ranking/pois?city=杭州` — 城市内景点被入选次数排序

**前端**
- 首页底部「热门城市 Top 10」横向滚动卡片
- 点击城市直接跳转到该城市生成行程

---

## 六、数据表设计

```sql
-- 用户表（无密码，验证码登录）
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(100) UNIQUE NOT NULL,
    nickname VARCHAR(50),
    avatar VARCHAR(255) DEFAULT '',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 验证码表
CREATE TABLE verification_codes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(100) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at DATETIME NOT NULL,
    used TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_email_expires (email, expires_at)
);

-- 行程表改造
ALTER TABLE saved_trips ADD COLUMN user_id INT DEFAULT NULL;
ALTER TABLE saved_trips ADD COLUMN is_public TINYINT DEFAULT 0;
ALTER TABLE saved_trips ADD COLUMN user_rating INT DEFAULT 0;
ALTER TABLE saved_trips ADD INDEX idx_user (user_id);
ALTER TABLE saved_trips ADD INDEX idx_public (is_public);

-- 收藏表
CREATE TABLE favorites (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    poi_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_poi (user_id, poi_id),
    INDEX idx_user (user_id)
);

-- 评论表
CREATE TABLE reviews (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    poi_id INT NOT NULL,
    rating INT NOT NULL DEFAULT 5,
    comment TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_poi (user_id, poi_id),
    INDEX idx_poi (poi_id)
);

-- 点赞表
CREATE TABLE trip_likes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    trip_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_trip (user_id, trip_id),
    INDEX idx_trip (trip_id)
);

-- 偏好模板表
CREATE TABLE preference_templates (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    name VARCHAR(50) NOT NULL,
    preferences_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id)
);

-- 差评行程景点记录（算法反馈）
CREATE TABLE bad_trip_pois (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    preferences_hash VARCHAR(64) NOT NULL,
    poi_ids_json TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_pref (user_id, preferences_hash)
);
```

---

## 七、实施优先级

| 优先级 | 功能 | 依赖 | 预计工作量 |
|---|---|---|---|
| P0 | 用户登录（验证码） | SMTP 邮件服务 | 1 天 |
| P0 | 行程绑定用户 | 用户登录 | 0.5 天 |
| P0 | 游客模式适配 | 行程绑定用户 | 0.5 天 |
| P1 | 景点详情卡片 | 无 | 0.5 天 |
| P1 | 景点收藏 | 用户登录 | 0.5 天 |
| P1 | 个人中心 | 用户登录 + 行程绑定 | 0.5 天 |
| P2 | 景点评分评论 | 用户登录 + 景点详情 | 1 天 |
| P2 | 偏好模板 | 用户登录 | 0.5 天 |
| P2 | 行程评价反馈 | 行程绑定用户 | 0.5 天 |
| P3 | 公开行程广场 | 行程绑定用户 | 1 天 |
| P3 | 城市热度排行 | 数据积累 | 0.5 天 |
| P3 | 行程点赞 | 用户登录 + 公开行程 | 0.5 天 |

---

## 八、验收标准

- [ ] 游客可生成行程，登录后可保存
- [ ] 验证码登录流程完整（发码 → 验证 → JWT）
- [ ] 登录后行程自动绑定用户，历史记录独立
- [ ] 景点详情弹窗显示完整信息 + 用户评论
- [ ] 登录用户可收藏景点，生成行程时收藏景点加权
- [ ] 登录用户可对景点评分评论
- [ ] 个人中心展示用户数据和收藏
- [ ] 偏好可保存为模板，一键复用
- [ ] 公开行程 > 20 条后广场自动开放
- [ ] 权限控制：用户只能编辑/删除自己的内容