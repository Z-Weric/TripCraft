# TripCraft 社区 + 攻略文章 + 美食广场 开发 TODO

> 核心流程：行程生成 → AI 一键生成攻略文章 → 预览编辑 → 发布到社区 / 导出 PDF

---

## 一、AI 攻略文章生成

### 1.1 后端：文章生成 API

**文件**：`backend/api/article.py`

**接口**：`POST /api/article/generate`

**请求体**：
```json
{
  "itinerary": { "行程 JSON" },
  "packed_items": ["防晒霜", "登山鞋", "双肩包"],
  "extra_foods": [{ "name": "外婆家", "description": "...", "price": 60 }]
}
```

**实现**：
- [ ] 构建 LLM prompt（小红书风格）
  - System prompt：你是小红书旅行博主，风格活泼有 emoji
  - User prompt：行程 JSON + 背包物品 + 额外美食
  - 输出要求：Markdown 格式，按文章结构模板
- [ ] 调用 LLM 生成文章
- [ ] 后处理：拼接明信片卡片标记 `<!--POSTCARD-->` 在文末
- [ ] 返回 Markdown 文章内容

**文章模板（prompt 中指定）**：
```
# {标题}

> 💰 总花费 ¥{total} | 📍 {destination} | ⏰ {days}天 | {preferences}

## Day 1 · {主题标题}

{景点体验描述，生动活泼，穿插实用 tips}

🍜 **午餐推荐**：{餐厅名} — {推荐理由}

## Day 2 · {主题标题}
...

## 🍜 美食推荐

### 行程中品尝的
- **{餐厅}** — {描述}

### 周边别错过
- **{餐厅}** — {描述}

## 📋 实用攻略

### 🎒 行前准备
{用户背包物品列表}

### 💰 花费明细
- 门票：¥{xxx}
- 交通：¥{xxx}
- 总计：¥{total}

### ⏰ 注意事项
{AI 生成的注意事项}
```

**预计工作量**：0.5 天

---

### 1.2 后端：美食推荐查询

**文件**：`backend/api/foods.py`

**接口**：
- `GET /api/foods?city=杭州&category=美食` — 城市美食列表
- `GET /api/foods/{id}` — 美食详情

**数据来源**：
- [ ] 从 POI 表查询 category='美食' 的景点
- [ ] 补充推荐理由（LLM 生成 or 手动编辑）

**预计工作量**：0.5 天

---

### 1.3 前端：文章预览编辑页

**文件**：
- `frontend/src/pages/ArticleEditor.tsx` — 文章预览编辑
- `frontend/src/components/MarkdownRenderer.tsx` — Markdown 渲染

**路由**：`/article/edit`

**功能**：
- [ ] 从行程页面点击「生成攻略」→ 跳转到文章编辑页
- [ ] 调用 `POST /api/article/generate` 获取 AI 文章
- [ ] Markdown 渲染预览（支持 emoji、标题、列表、引用）
- [ ] 可编辑模式：用户可修改文章内容
- [ ] 文末展示 3D 翻转明信片（可交互）
- [ ] 底部两个按钮：[发布到社区] [导出攻略卡片]

**数据传递**：
- 行程 JSON 从 itineraryStore 获取
- 背包物品从 PackingList 状态获取
- 额外美食从后端查询获取

**预计工作量**：1 天

---

## 二、社区系统

### 2.1 后端：帖子 + 评论

**文件**：`backend/api/community.py`

**数据模型**：
```sql
CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,           -- Markdown
    cover_image VARCHAR(255),
    city VARCHAR(50),
    tags VARCHAR(255),               -- 攻略/感悟/美食/住宿
    trip_id INT,                     -- 关联行程
    trip_json TEXT,                  -- 行程 JSON（用于明信片渲染）
    view_count INT DEFAULT 0,
    like_count INT DEFAULT 0,
    comment_count INT DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME,
    INDEX idx_user (user_id),
    INDEX idx_city (city),
    INDEX idx_created (created_at)
);

CREATE TABLE post_comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME,
    INDEX idx_post (post_id)
);

CREATE TABLE post_likes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    post_id INT NOT NULL,
    UNIQUE KEY uk_user_post (user_id, post_id)
);
```

**API**：
- [ ] `GET /api/posts?page=1&tag=xxx&city=xxx` — 帖子列表（分页 10 条/页）
- [ ] `GET /api/posts/{id}` — 帖子详情（含 trip_json）
- [ ] `POST /api/posts` — 发布帖子（需登录）
- [ ] `PUT /api/posts/{id}` — 编辑帖子（仅作者）
- [ ] `DELETE /api/posts/{id}` — 删除帖子（仅作者）
- [ ] `POST /api/posts/{id}/like` — 点赞（需登录）
- [ ] `DELETE /api/posts/{id}/like` — 取消点赞
- [ ] `GET /api/posts/{id}/comments` — 评论列表
- [ ] `POST /api/posts/{id}/comments` — 发评论（需登录）
- [ ] `DELETE /api/comments/{id}` — 删除评论（仅作者）

**MySQL 建表**：
- [ ] 创建 posts / post_comments / post_likes 三张表

**预计工作量**：1 天

---

### 2.2 前端：社区列表页

**文件**：`frontend/src/pages/Community.tsx`

**路由**：`/community`

**功能**：
- [ ] 帖子卡片瀑布流（封面图 + 标题 + 作者 + 点赞数 + 评论数）
- [ ] 顶部筛选 tabs：全部 / 攻略 / 感悟 / 美食 / 住宿
- [ ] 城市筛选下拉
- [ ] 分页加载（滚动到底部自动加载下一页）
- [ ] 点击卡片进入帖子详情

**预计工作量**：1 天

---

### 2.3 前端：帖子详情页

**文件**：`frontend/src/pages/PostDetail.tsx`

**路由**：`/post/:id`

**功能**：
- [ ] Markdown 文章渲染（复用 MarkdownRenderer）
- [ ] 文末 3D 翻转明信片（从 trip_json 渲染）
- [ ] 点赞按钮 + 数量
- [ ] 评论列表 + 评论输入框
- [ ] 作者信息卡片
- [ ] 「生成我的行程」按钮（从帖子关联的行程跳转到行程生成）
- [ ] 底部操作栏：[导出攻略卡片] [生成类似行程]

**预计工作量**：1 天

---

## 三、导出 PDF（攻略卡片）

### 3.1 前端：精简攻略卡片模板

**文件**：`frontend/src/components/ArticleCard.tsx`

**功能**：
- [ ] 精简一页纸布局：
  - 顶部：标题 + 摘要信息
  - 中间：每日路线（只列时间 + 景点名 + 花费）
  - 底部：美食列表 + 装备列表 + 总花费
  - 末尾：明信片正面静态截图
- [ ] 打印 CSS 样式（A4 纸、合理分页）

### 3.2 打印样式

**文件**：`frontend/src/index.css`

- [ ] `@media print` 控制：
  - 隐藏所有 `.no-print` 元素（按钮、导航、评论）
  - 明信片改为静态正面展示
  - 文章内容 A4 纸宽、12pt 字号
  - 每天行程 `page-break-inside: avoid`

**预计工作量**：0.5 天

---

## 四、美食广场

### 4.1 后端：美食 API

**文件**：`backend/api/foods.py`

**数据**：
- [ ] 复用 POI 表中 category='美食' 的数据
- [ ] 新增 `foods` 表存储美食详情（菜系、介绍、推荐餐厅）
- [ ] 或者直接用 POI 表 + 额外字段

**API**：
- [ ] `GET /api/foods?city=杭州` — 城市美食列表
- [ ] `GET /api/foods/{id}` — 美食详情
- [ ] `POST /api/foods` — 用户投稿（需登录）

### 4.2 前端：美食广场页

**文件**：`frontend/src/pages/FoodPlaza.tsx`

**路由**：`/food`

**功能**：
- [ ] 顶部城市筛选 tabs
- [ ] 美食卡片网格（图片 + 名称 + 菜系 + 人均 + 评分）
- [ ] 点击卡片弹出详情弹窗（复用 PoiDetailModal）
- [ ] 「加入我的行程」按钮

**预计工作量**：1 天

---

## 五、入口页 + 导航改造

### 5.1 入口页

**文件**：`frontend/src/pages/Welcome.tsx`

- [ ] 增加功能入口：美食广场 / 旅游社区

### 5.2 顶栏导航

**文件**：`frontend/src/pages/Home.tsx` + 全局

- [ ] 顶栏增加：美食广场 | 社区 导航链接
- [ ] 行程生成后增加「生成攻略」按钮

**预计工作量**：0.5 天

---

## 六、实施顺序

| 顺序 | 模块 | 依赖 | 工作量 |
|---|---|---|---|
| 1 | AI 攻略文章生成（后端） | 行程数据（已有） | 0.5 天 |
| 2 | 文章预览编辑页（前端） | 1 | 1 天 |
| 3 | 社区系统（后端） | MySQL | 1 天 |
| 4 | 社区列表 + 详情页（前端） | 3 | 2 天 |
| 5 | 导出 PDF（前端） | 2 | 0.5 天 |
| 6 | 美食广场（后端 + 前端） | POI 数据 | 1 天 |
| 7 | 入口页 + 导航改造 | 全部 | 0.5 天 |
| **总计** | | | **6.5 天** |

---

## 七、数据流图

```
行程生成（Home）
  ├── Packing 背包（选物品）
  └── 点击「生成攻略」
        ↓
ArticleEditor（预览编辑）
  ├── 后端 POST /api/article/generate
  │     输入：行程 JSON + 背包物品 + 额外美食
  │     输出：Markdown 文章
  └── 用户编辑确认
        ↓
    ┌───┴───┐
    │       │
  发布     导出 PDF
    │       │
    ↓       ↓
Community  ArticleCard
（帖子列表） （打印精简卡片）
    │
    ↓
PostDetail（帖子详情）
  ├── 文章渲染
  ├── 3D 明信片
  ├── 点赞 + 评论
  └── 「生成我的行程」→ 回到 Home
```

---

## 八、验收标准

- [ ] 点击「生成攻略」后 AI 在 30 秒内返回小红书风格文章
- [ ] 文章包含：每日行程描述 + 美食推荐 + 实用攻略 + 明信片
- [ ] 文章可编辑修改
- [ ] 发布到社区后可在社区列表看到
- [ ] 帖子详情页可点赞、评论
- [ ] 导出 PDF 为精简一页纸攻略卡片
- [ ] 美食广场展示各城市美食卡片
- [ ] 帖子详情页「生成我的行程」可跳转到行程生成