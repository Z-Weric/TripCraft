# TripCraft v2.0 升级计划

> 基于 v1 全量代码审计，按「分阶段迭代」策略推进，覆盖性能优化、功能升级、新增需求、架构工程质量、UI/UX 提升五个方向。

---

## 一、v1 现状审计

### 1.1 技术栈

| 层 | 技术 | 版本 |
|---|---|---|
| 前端框架 | React + TypeScript | React 19.2, TS 6.0 |
| 构建工具 | Vite | 8.1 |
| UI 库 | Ant Design + Tailwind CSS | Antd 6.5, Tailwind 3.4 |
| 地图 | react-leaflet | 5.0 |
| 图表 | echarts-for-react | 3.0 |
| 后端 | FastAPI + SQLAlchemy | FastAPI 0.111 |
| 数据库 | SQLite | - |
| RAG | scikit-learn TF-IDF + jieba | - |
| LLM | 硅基流动 LongCat-2.0 | - |
| 地图 API | 高德 Web API | - |

### 1.2 代码规模

- 前端：7 个组件 + 1 个 API 服务文件，~1200 行
- 后端：6 个 API 路由 + 5 个 service + 1 个数据模型，~800 行
- 种子数据：10 城市 55 个 POI

### 1.3 核心问题清单

| # | 问题 | 影响 | 所在文件 |
|---|---|---|---|
| P1 | 前端无路由体系，单页面承载全部功能 | 无法扩展多页面（历史/详情/分享） | `App.tsx` |
| P2 | zustand 已安装但未使用，状态全在 App 组件内 useState | 状态无法跨组件共享，重新生成逻辑脆弱 | `App.tsx:13-17` |
| P3 | API baseURL 硬编码 `http://localhost:8000` | 部署后无法切换环境 | `api.ts:3` |
| P4 | 无代码分割/懒加载，ECharts/Leaflet/Antd 全量加载 | 首屏体积过大 | `main.tsx` |
| P5 | 后端全同步阻塞，httpx 用同步 client | 高并发下性能瓶颈 | `llm_service.py`, `amap_service.py` |
| P6 | `verify_itinerary` 中 `verify_spot_poi` 被调用两次（一次 for all，一次 for count） | 验证耗时翻倍 | `verify_service.py:66-74` |
| P7 | 模型服务是 mock（随机打乱 POI + 固定时段），未接入 LLM | 行程质量低，无智能排布 | `model_service.py:57` |
| P8 | RAG 索引每次启动重建，无持久化 | 启动慢 | `main.py:33-48` |
| P9 | .env 含明文 API Key 已提交 Git | 安全风险 | `backend/.env` |
| P10 | 无日志体系，异常静默吞掉 | 线上问题无法排查 | 全局 |
| P11 | 无测试 | 回归风险 | 全局 |
| P12 | 前端组件无错误边界 | 单组件崩溃白屏 | 全局 |
| P13 | 无行程持久化，刷新即丢失 | 用户无法回看 | 全局 |
| P14 | 桌宠 chat 未传递 destination 上下文 | 回答不够精准 | `TravelPet.tsx:60` |
| P15 | MapView 图标依赖 CDN unpkg | 离线/网络异常时图标断裂 | `MapView.tsx:8-11` |

---

## 二、Phase 1 — 地基加固（性能 + 架构工程质量）

> 目标：不改变用户可见功能，但让代码结构、性能、安全性达到可扩展水平。

### 2.1 前端架构重构

#### 2.1.1 引入 React Router 路由体系

**现状**：`App.tsx` 是唯一页面，所有内容堆在一个组件里。

**升级**：
```
src/
├── routes/
│   ├── index.tsx          # 路由配置
│   ├── Home.tsx           # 首页（搜索 + 生成结果）
│   ├── History.tsx        # 历史行程列表
│   └── Detail.tsx         # 行程详情（分享链接可访问）
├── App.tsx                # 改为 <RouterProvider>
```

**改动文件**：新增 `routes/`，重写 `App.tsx`，`main.tsx` 注入 router。

#### 2.1.2 zustand 全局状态管理

**现状**：`App.tsx` 用 4 个 useState 管理全局状态。

**升级**：
```typescript
// src/stores/itineraryStore.ts
interface TripState {
  loading: boolean;
  itinerary: Itinerary | null;
  verification: Verification | null;
  error: string | null;
  lastRequest: GenerateRequest | null;
  history: SavedTrip[];           // 本地存储的行程历史
  generate: (req: GenerateRequest) => Promise<void>;
  regenerate: () => void;
  saveToHistory: () => void;
  loadFromHistory: (id: string) => void;
  clearHistory: () => void;
}
```

**改动文件**：新增 `stores/itineraryStore.ts`，重写 `App.tsx` 消费 store。

#### 2.1.3 代码分割与懒加载

**现状**：`main.tsx` 直接 import App，所有组件同步加载。

**升级**：
- `React.lazy` + `Suspense` 懒加载路由组件
- ECharts、Leaflet 按需动态 import
- Antd 组件已支持 tree-shaking，无需额外处理

**预期收益**：首屏 JS 体积减少 ~40%（ECharts ~400KB + Leaflet ~150KB 延迟加载）。

#### 2.1.4 API 环境变量配置

**现状**：`const API_BASE = "http://localhost:8000"` 硬编码。

**升级**：
```typescript
// src/services/config.ts
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
export { API_BASE };
```
- `.env.development` / `.env.production` 分环境配置
- `.gitignore` 添加 `.env.local`

#### 2.1.5 前端错误边界

**升级**：新增 `ErrorBoundary.tsx`，包裹路由组件，崩溃时显示友好降级 UI。

### 2.2 后端架构重构

#### 2.2.1 异步化

**现状**：所有路由和 service 用同步 `def` + `httpx.get/post`。

**升级**：
- 路由改为 `async def`
- `httpx.Client` → `httpx.AsyncClient`（全局单例复用连接池）
- SQLAlchemy 2.0 async session

**改动文件**：`main.py`、`api/*.py`、`services/llm_service.py`、`services/amap_service.py`、`database/models.py`

#### 2.2.2 统一异常处理

**现状**：异常被 try/except 吞掉或直接 500。

**升级**：
```python
# api/errors.py
class TripCraftError(Exception):
    code: str
    message: str

class POINotFoundError(TripCraftError): ...
class LLMUnavailableError(TripCraftError): ...
class BudgetExceededError(TripCraftError): ...

# main.py 注册全局异常处理
@app.exception_handler(TripCraftError)
async def trip_error_handler(request, exc): ...
```

#### 2.2.3 结构化日志

**升级**：
```python
# utils/logger.py
import logging, json
class JsonFormatter(logging.Formatter): ...
logger = logging.getLogger("tripcraft")
```
- 每个请求记录：method, path, status, duration, error
- LLM 调用记录：model, tokens, latency

#### 2.2.4 Pydantic Settings 环境管理

**现状**：手动读 .env 文件，`line.startswith("KEY=")` 解析。

**升级**：
```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    amap_api_key: str = ""
    siliconflow_api_key: str = ""
    llm_model: str = "meituan-longcat/LongCat-2.0"
    database_url: str = "sqlite:///data/tripcraft.db"
    model_config = SettingsConfigDict(env_file=".env")
```

#### 2.2.5 数据库优化

**升级**：
- SQLite WAL 模式：`PRAGMA journal_mode=WAL`
- 添加索引：`POI.category`、`POI.lat`、`POI.lng`（已有 city 索引）
- 连接池：`pool_size=10, max_overflow=20`（SQLite 用 `StaticPool`）

#### 2.2.6 缓存机制

**升级**：
- POI 查询结果缓存（functools.lru_cache 或内存 dict + TTL）
- RAG TF-IDF 索引持久化到 `data/tfidf_index.pkl`，启动时加载
- 高德 API 验证结果缓存（同一景点名+坐标 24h 内不重复请求）

#### 2.2.7 验证服务优化

**现状**：`verify_itinerary` 中对每个 item 调用 `verify_spot_poi` 两次。

**升级**：改为一次遍历，同时收集 valid 标记和计数：
```python
verified_count = 0
for item in all_items:
    if verify_spot_poi(item["spot"], item["lat"], item["lng"], known_pois):
        verified_count += 1
results["spots_valid"] = verified_count == len(all_items)
results["spots_verified"] = verified_count
```

### 2.3 安全修复

- `.env` 从 Git 移除（`git rm --cached`），提供 `.env.example`
- `.gitignore` 添加 `.env`、`data/*.db`、`data/*.pkl`
- API Key 通过环境变量注入，不落盘

### 2.4 Phase 1 交付物

| 交付项 | 文件 |
|---|---|
| 路由体系 | `src/routes/index.tsx`, `Home.tsx`, `History.tsx` |
| 状态管理 | `src/stores/itineraryStore.ts` |
| 懒加载 | 路由组件 lazy import |
| API 配置 | `src/services/config.ts`, `.env.development` |
| 错误边界 | `src/components/ErrorBoundary.tsx` |
| 异步后端 | 全部 `api/*.py`, `services/*.py` |
| 异常处理 | `api/errors.py`, `main.py` |
| 日志体系 | `utils/logger.py` |
| 环境管理 | `config.py`, `.env.example` |
| DB 优化 | `database/models.py` |
| 缓存 | `services/cache.py`, RAG 持久化 |
| 安全 | `.gitignore`, `git rm --cached backend/.env` |

---

## 三、Phase 2 — 功能升级

> 目标：提升行程生成质量和用户体验，让系统从「mock 玩具」变成「可用工具」。

### 3.1 行程生成流式输出

**现状**：`POST /api/generate` 同步返回完整 JSON，用户等待 5-10s 无反馈。

**升级**：
- 新增 `POST /api/generate/stream` SSE 接口
- 分阶段推送：`{type: "rag_retrieval", content: "正在检索景点..."}` → `{type: "llm_generating", content: "正在生成行程..."}` → `{type: "verifying", content: "正在验证..."}` → `{type: "done", itinerary: {...}, verification: {...}}`
- 前端 SearchBar 生成按钮改为流式进度展示

**改动文件**：新增 `api/generate_stream.py`，前端 `App.tsx` / `stores/itineraryStore.ts`

### 3.2 LLM 真实生成替换 Mock

**现状**：`model_service.py` 随机打乱 POI，固定时段填入。

**升级**：
```python
async def generate_itinerary_llm(destination, days, budget, preferences, pois):
    system_prompt = f"""你是旅行规划专家。根据以下景点数据生成 {days} 天行程 JSON。
    约束：总花费 ≤ {budget} 元，每日 3-4 个景点，路线就近排布。
    返回 JSON 格式：{schema}
    
    可选景点：
    {json.dumps(pois, ensure_ascii=False)}
    """
    result = await chat_completion_async([{"role":"system","content":system_prompt}])
    return json.loads(result)
```
- 保留 mock 作为降级方案（LLM 不可用时自动回退）
- 增加 JSON schema 校验，LLM 输出不合法时重试一次

**改动文件**：`services/model_service.py`

### 3.3 行程持久化 + 历史记录

**现状**：行程生成后存在内存，刷新即丢失。

**升级**：

后端：
- 新增 `Itinerary` 和 `ItineraryItem` 数据模型
- `POST /api/itineraries` 保存行程
- `GET /api/itineraries` 列表
- `GET /api/itineraries/{id}` 详情
- `DELETE /api/itineraries/{id}` 删除

前端：
- 生成行程后自动保存
- 新增 `/history` 路由页面，展示历史行程卡片列表
- 点击卡片进入详情或重新生成

**改动文件**：`database/models.py`, 新增 `api/itineraries.py`, 前端 `routes/History.tsx`

### 3.4 行程编辑功能

**现状**：行程生成后不可修改。

**升级**：
- 时间线支持拖拽排序景点（dnd-kit 或 @dnd-kit/core）
- 每个景点卡片增加「替换」按钮，从同城市同类别 POI 中选择替代
- 每日景点数量可增减
- 编辑后实时更新地图路线和费用图表
- 编辑后可重新保存

**改动文件**：`components/ItineraryTimeline.tsx` 大幅升级，新增 `components/SpotReplaceModal.tsx`

### 3.5 用户偏好权重系统

**现状**：偏好只做简单 category 过滤，匹配即选中。

**升级**：
- 偏好标签支持权重（1-5 星）
- RAG 检索时按权重加权打分
- 生成行程时按权重决定各类别景点比例

**改动文件**：`components/SearchBar.tsx`，`services/rag_service.py`，`services/model_service.py`

### 3.6 桌宠上下文增强

**现状**：`TravelPet.tsx:60` 调用 chatWithPetStream 时 destination 传 undefined。

**升级**：
- 从 store 读取当前行程的 destination
- 桌宠知道当前在看哪个城市，回答更精准
- 增加行程相关快捷问题（"这个城市还有什么隐藏景点？"）

**改动文件**：`components/TravelPet.tsx`，`stores/itineraryStore.ts`

### 3.7 Phase 2 交付物

| 交付项 | 文件 |
|---|---|
| 流式生成 | `api/generate_stream.py`, `stores/itineraryStore.ts` |
| LLM 生成 | `services/model_service.py` 重写 |
| 行程持久化 | `database/models.py`, `api/itineraries.py` |
| 历史记录 | `routes/History.tsx`, `api/itineraries.py` |
| 行程编辑 | `components/ItineraryTimeline.tsx`, `components/SpotReplaceModal.tsx` |
| 偏好权重 | `components/SearchBar.tsx`, `services/rag_service.py` |
| 桌宠增强 | `components/TravelPet.tsx` |

---

## 四、Phase 3 — 新增需求

> 目标：扩展产品边界，从单次生成工具进化为旅行规划平台。

### 4.1 行程分享

- 生成行程后产出分享短链 `POST /api/share` → 返回 `/detail/{token}`
- 分享页面只读模式，含明信片 + 地图 + 花费
- 支持导出 JSON / Markdown 格式

**新增文件**：`api/share.py`, `routes/Detail.tsx`, `components/ShareModal.tsx`

### 4.2 天气集成

- 接入免费天气 API（如 OpenWeatherMap 或高德天气 API）
- 行程页面展示每日天气预报（温度、天气状况、穿衣建议）
- 恶劣天气时在景点旁标注提醒

**新增文件**：`services/weather_service.py`, `api/weather.py`, `components/WeatherCard.tsx`

### 4.3 Packing 清单

- 根据目的地、天数、季节、偏好自动生成行李清单
- 清单可勾选、可编辑、可导出
- 数据来源：规则引擎 + LLM 生成

**新增文件**：`services/packing_service.py`, `api/packing.py`, `components/PackingList.tsx`

### 4.4 动态 POI 补充

**现状**：只有 55 个种子 POI，用户搜索不在列表的城市返回 error。

**升级**：
- 用户输入新城市时，自动调用高德 POI API 拉取该城市 top 20 景点
- 拉取结果存入数据库，下次直接查询
- RAG 索引增量更新

**改动文件**：`services/amap_service.py`，`services/rag_service.py`，`api/generate.py`

### 4.5 多目的地联程

- 搜索栏支持添加多个城市 + 各城市天数
- 行程生成时按城市顺序排布，含城际交通建议
- 地图展示跨城市路线

**改动文件**：`components/SearchBar.tsx`，`api/generate.py`，`services/model_service.py`，`components/MapView.tsx`

### 4.6 Phase 3 交付物

| 交付项 | 文件 |
|---|---|
| 行程分享 | `api/share.py`, `routes/Detail.tsx`, `components/ShareModal.tsx` |
| 天气集成 | `services/weather_service.py`, `api/weather.py`, `components/WeatherCard.tsx` |
| Packing 清单 | `services/packing_service.py`, `api/packing.py`, `components/PackingList.tsx` |
| 动态 POI | `services/amap_service.py`, `services/rag_service.py` |
| 多目的地 | `SearchBar.tsx`, `generate.py`, `model_service.py`, `MapView.tsx` |

---

## 五、Phase 4 — UI/UX 提升

> 目标：在 Postcard 设计语言内提升视觉层次、交互体验和可访问性。

### 5.1 深色模式（Postcard Night）

- 新增暗色色板：墨蓝纸底 `#1A1814`、暖灰文 `#D4C5B0`、赤陶保留 `#C9622A`
- 顶栏增加切换开关
- CSS 变量驱动，`prefers-color-scheme: dark` 自动适配

**改动文件**：`index.css`，`tailwind.config.js`，`App.tsx`（切换器）

### 5.2 移动端深度适配

- 搜索栏表单改为移动端全屏弹窗
- 明信片正面/背面改为移动端上下堆叠（非 3D 翻转）
- 地图改为可展开/收起的手风琴
- 桌宠面板移动端全屏

**改动文件**：全局响应式 CSS，各组件增加移动端分支

### 5.3 动画体验升级

- 行程生成流式展示：逐日「打印」效果（明信片打印机隐喻）
- 时间线景点卡片 stagger 入场
- 地图标记逐个「盖章」入场
- 花费图表数字滚动动画

**改动文件**：`index.css` keyframes，各组件 animation props

### 5.4 无障碍改进

- 所有交互元素添加 ARIA label
- 键盘导航支持（Tab 序列、Enter/Space 触发）
- 颜色对比度全面审计（当前弱文 3.9:1 不达标）
- screen reader 友好（行程结构语义化）

**改动文件**：全局

### 5.5 MapView 离线图标修复

**现状**：Leaflet 图标从 unpkg CDN 加载。

**升级**：将 marker 图标放入 `public/leaflet-icons/`，本地引用。

**改动文件**：`MapView.tsx`

### 5.6 Phase 4 交付物

| 交付项 | 文件 |
|---|---|
| 深色模式 | `index.css`, `tailwind.config.js` |
| 移动适配 | 全局 CSS + 组件 |
| 动画升级 | `index.css`, 各组件 |
| 无障碍 | 全局 |
| 地图离线 | `MapView.tsx`, `public/leaflet-icons/` |

---

## 六、实施时间线

| Phase | 预计工作量 | 依赖 | 可交付状态 |
|---|---|---|---|
| Phase 1 | 2-3 天 | 无 | 功能不变，性能和代码质量显著提升 |
| Phase 2 | 3-4 天 | Phase 1 | 核心功能可用（LLM 生成 + 持久化 + 编辑） |
| Phase 3 | 3-4 天 | Phase 2 | 产品功能完整（分享 + 天气 + 清单 + 动态 POI） |
| Phase 4 | 2-3 天 | Phase 1-3 | 体验打磨完成 |

每个 Phase 完成后做一次完整测试和代码审查，确保不回退。

---

## 七、风险与降级策略

| 风险 | 降级方案 |
|---|---|
| LLM API 不可用/超时 | 回退到 mock 模型生成 |
| 高德 API 限流 | 回退到本地 POI 数据库验证 |
| SQLite 并发不足 | 预留 PostgreSQL 迁移接口 |
| RAG 向量索引构建慢 | 持久化 + 增量更新 |
| 前端体积过大 | 持续监控 bundle size，动态 import |

---

## 八、验收标准

### Phase 1 验收
- [ ] 首屏 JS 体积减少 ≥30%
- [ ] 后端 API 响应时间 P50 ≤200ms（不含 LLM 调用）
- [ ] .env 不在 Git 中
- [ ] 统一日志格式，可查询
- [ ] 前端错误边界生效

### Phase 2 验收
- [ ] 行程生成有流式进度反馈
- [ ] LLM 生成行程 JSON 合法率 ≥95%
- [ ] 刷新页面后历史行程可恢复
- [ ] 行程可编辑并重新保存
- [ ] 桌宠回答带城市上下文

### Phase 3 验收
- [ ] 分享链接可被他人打开
- [ ] 天气信息正确展示
- [ ] Packing 清单可勾选导出
- [ ] 新城市自动补充 POI

### Phase 4 验收
- [ ] 深色模式全组件适配
- [ ] 移动端 375px 宽度下可用
- [ ] Lighthouse 无障碍评分 ≥90
- [ ] 地图图标离线可用