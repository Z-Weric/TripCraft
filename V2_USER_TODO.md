# TripCraft 用户详细信息页 — 开发流程 TODO

> 按「先做不依赖新业务的，再做需要补 API 的」分两步走。
> 每个模块开始前先和用户确认设计方案。

---

## 第一步：不依赖新业务的模块（现在就能做）

### 1.1 基本信息 + 账号安全（合并为一个设置区）

**前端**
- [ ] Profile 页面顶部用户信息卡增加「编辑」按钮
- [ ] 弹出编辑弹窗：修改昵称（头像暂用首字母）
- [ ] 底部增加「退出登录」按钮（已有，移到设置区内）
- [ ] 增加用户信息展示：注册时间

**后端**
- [ ] `PUT /api/auth/profile` 已有，确认 nickname 修改正常工作

**依赖**：无
**预计工作量**：0.5 天

---

### 1.2 旅行统计仪表盘

**前端**
- [ ] Profile 页面用户信息卡下方增加统计区
- [ ] 4 个数字卡片：总行程数、总旅行天数、去过城市数、总花费
- [ ] 数据来源：已有的 `GET /api/itineraries` 返回列表本地计算

**后端**
- [ ] 新增 `GET /api/user/stats` — 返回聚合统计（行程数、天数、城市数、总花费、收藏数、评论数）
- [ ] SQL：`SELECT COUNT(*), SUM(days), COUNT(DISTINCT destination), SUM(total_cost) FROM saved_trips WHERE user_id=?`

**依赖**：行程数据（已有）
**预计工作量**：0.5 天

---

### 1.3 我的行程（已有基础，优化展示）

**前端**
- [ ] 行程卡片增加「公开/私有」切换按钮
- [ ] 行程卡片显示评分（如有）
- [ ] 点击行程卡片跳转到只读详情页（复用 `/detail/:token` 或新增 `/trip/:id`）
- [ ] 空状态优化：引导用户去生成行程

**后端**
- [ ] `PUT /api/itineraries/{id}/visibility` 已有
- [ ] `PUT /api/itineraries/{id}/rate` 已有
- [ ] 新增 `GET /api/itineraries/{id}` 详情接口已有

**依赖**：行程 CRUD（已有）
**预计工作量**：0.5 天

---

### 1.4 收藏景点（已有基础，优化展示）

**前端**
- [ ] 收藏列表按城市分组展示
- [ ] 每个景点可点击打开景点详情弹窗（PoiDetailModal）
- [ ] 收藏列表支持取消收藏
- [ ] 增加城市筛选下拉框

**后端**
- [ ] `GET /api/favorites` 已支持 city 参数过滤
- [ ] `DELETE /api/pois/{id}/favorite` 已有

**依赖**：收藏 API（已有）+ PoiDetailModal（已有）
**预计工作量**：0.5 天

---

### 1.5 旅行足迹地图

**前端**
- [ ] Profile 页面新增「旅行足迹」Tab
- [ ] 用 Leaflet 地图展示去过的城市（基于行程 destination）
- [ ] 每个城市放一个彩色标记，标记内显示行程次数
- [ ] 点击标记显示该城市的行程列表

**后端**
- [ ] `GET /api/user/cities` — 返回用户去过的城市列表 + 每城市行程数
- [ ] SQL：`SELECT destination, COUNT(*) as count FROM saved_trips WHERE user_id=? GROUP BY destination`
- [ ] 需要返回城市经纬度（从 POI 表取该城市第一个景点的坐标，或内置城市坐标）

**依赖**：行程数据（已有）+ Leaflet（已有）
**预计工作量**：0.5 天

---

## 第二步：需要先补后端 API 的模块

### 2.1 我的评论历史

**后端**
- [ ] 新增 `GET /api/user/reviews` — 当前用户所有评论列表
- [ ] 返回：景点名、城市、评分、评论内容、时间
- [ ] SQL：`SELECT r.*, p.name, p.city FROM reviews r JOIN pois p ON r.poi_id = p.id WHERE r.user_id=?`

**前端**
- [ ] Profile 新增「我的评论」Tab
- [ ] 评论卡片：景点名 + 评分 + 评论内容 + 时间
- [ ] 支持删除自己的评论

**依赖**：后端评论查询 API
**预计工作量**：0.5 天

---

### 2.2 偏好设置

**后端**
- [ ] `users` 表新增字段：`default_preferences`（JSON）、`default_budget`（INT）、`default_days`（INT）
- [ ] `PUT /api/user/preferences` — 保存默认偏好
- [ ] `GET /api/user/preferences` — 读取默认偏好
- [ ] 偏好模板 API：
  - `POST /api/templates` — 保存模板
  - `GET /api/templates` — 模板列表
  - `DELETE /api/templates/{id}` — 删除模板
- [ ] `preference_templates` 表已有

**前端**
- [ ] Profile 新增「偏好设置」区域
- [ ] 默认偏好编辑：偏好标签权重 + 默认预算 + 默认天数
- [ ] 偏好模板列表：保存当前偏好为模板、删除模板
- [ ] Home 页 SearchBar 从 `GET /api/user/preferences` 加载默认值

**依赖**：后端偏好 API + users 表改造
**预计工作量**：1 天

---

### 2.3 账号注销

**后端**
- [ ] `DELETE /api/auth/account` — 注销账号
- [ ] 级联删除：users + saved_trips + favorites + reviews + preference_templates + verification_codes
- [ ] 需要二次确认（前端弹窗 + 后端验证码确认）

**前端**
- [ ] 设置区底部「注销账号」按钮（红色危险操作）
- [ ] 弹窗确认：输入验证码确认注销
- [ ] 注销后清除 localStorage + 跳转到入口页

**依赖**：后端注销 API
**预计工作量**：0.5 天

---

### 2.4 成就/勋章系统

**后端**
- [ ] 设计成就规则（存代码或数据库）：
  - `first_trip` — 首次生成行程
  - `explorer_3` — 去 3 个不同城市
  - `explorer_5` — 去 5 个不同城市
  - `explorer_10` — 去 10 个不同城市
  - `collector_5` — 收藏 5 个景点
  - `collector_20` — 收藏 20 个景点
  - `reviewer_1` — 首次评论
  - `reviewer_10` — 10 条评论
  - `planner_10` — 生成 10 份行程
  - `big_spender` — 单次行程花费超过 5000
- [ ] `GET /api/user/achievements` — 返回已解锁成就 + 进度
- [ ] `user_achievements` 表：user_id, achievement_code, unlocked_at

**前端**
- [ ] Profile 新增「成就墙」区域
- [ ] 勋章网格展示：已解锁高亮、未解锁灰色 + 进度条
- [ ] 解锁动画

**依赖**：成就规则 + user_achievements 表
**预计工作量**：1 天

---

## 时间线

| 步骤 | 模块 | 工作量 | 依赖 |
|---|---|---|---|
| 第一步 | 1.1 基本信息 | 0.5 天 | 无 |
| 第一步 | 1.2 旅行统计 | 0.5 天 | 无 |
| 第一步 | 1.3 我的行程优化 | 0.5 天 | 无 |
| 第一步 | 1.4 收藏景点优化 | 0.5 天 | 无 |
| 第一步 | 1.5 旅行足迹地图 | 0.5 天 | 新增 1 个 API |
| 第二步 | 2.1 我的评论 | 0.5 天 | 新增 1 个 API |
| 第二步 | 2.2 偏好设置 | 1 天 | users 表改造 + 模板 API |
| 第二步 | 2.3 账号注销 | 0.5 天 | 新增 1 个 API |
| 第二步 | 2.4 成就系统 | 1 天 | 规则设计 + 建表 |

**第一步合计**：2.5 天
**第二步合计**：3 天
**总计**：5.5 天

---

## 注意事项

1. 每个模块开始前先和用户确认设计方案
2. 后端 API 写完立即用 curl 测试
3. 前端组件写完立即用 tsc 验证编译
4. 每步完成后提交 Git