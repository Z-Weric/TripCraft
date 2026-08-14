# TripCraft AI 架构开发待办

> 来源：[AI_ARCHITECTURE_OPTIMIZATION.md](AI_ARCHITECTURE_OPTIMIZATION.md)
> 原则：按阶段顺序开发；每项完成后补测试、更新状态，并记录实际改动与验证结果。
> 当前阶段：Phase 3 - 训练数据闭环与本地微调

---

## 开发约定

- [ ] 每次改动前确认相关接口的现状与调用方，避免流式/非流式行为不一致。
- [ ] 每个后端接口改动至少增加或更新对应自动化测试；暂不具备测试框架时，以可复现的 API 验证命令记录在 PR/提交说明中。
- [ ] 所有模型输出先做 Schema 校验和业务校验，校验失败不直接返回前端。
- [ ] 涉及用户数据、分享、认证的改动必须覆盖未登录、非所有者、所有者和公开资源四类场景。
- [ ] 不在训练数据、日志或外部模型请求中记录密钥、邮箱或可识别个人信息。

---

## Phase 0 - 正确性与安全性

目标：消除现有链路的高风险不一致、虚假验证与越权风险，为后续架构拆分建立可靠基础。

### 0.1 统一生成请求与生成编排

- [x] 提取共享的 `GenerateRequest` 和响应模型，供 `/api/generate` 与 `/api/generate/stream` 使用。
  - 文件：新增 `backend/schemas/generate.py`，修改 `backend/api/generate.py`、`backend/api/generate_stream.py`
  - 验收：两个接口均支持 `destination`、`days`、`budget`、`preferences`、`favorite_poi_ids`。
- [x] 在流式链路把 `favorite_poi_ids` 传入 `generate_itinerary()`。
  - 文件：`backend/api/generate_stream.py`
  - 验收：收藏 POI 在流式和非流式请求中得到相同的排序加权结果。
- [x] 提取共同的“查询 POI -> RAG 召回 -> 调用生成 -> 验证”编排服务，避免两条接口分别维护。
  - 文件：新增 `backend/services/generation_service.py`
  - 验收：流式与非流式除传输方式外的候选 POI、规划结果和验证逻辑一致。
- [x] 为生成请求添加边界校验。
  - 规则：`days`、`budget` 为正数，偏好数量和长度受限，目的地去除空白并限制长度。
  - 验收：非法请求返回明确的 4xx 错误，不触发模型或外部 API 调用。

### 0.2 修复事实验证

- [x] 无高德 Key 时，`verify_spot()` 改为返回“无法通过外部验证”的状态，而不是无条件验证成功。
  - 文件：`backend/services/amap_service.py`
  - 验收：无 Key 情况下由 `verify_spot_poi()` 使用本地 POI 的名称和坐标精确匹配完成验证。
- [x] 为验证结果区分“已验证”“本地验证”“无法验证”“验证失败”。
  - 文件：`backend/services/verify_service.py`、`backend/schemas/generate.py`
  - 验收：前端和日志能识别验证来源，不能把“未验证”显示为“已通过”。
- [x] 在验证中检查必填字段、日数、景点数量、景点重复、POI 引用、金额计算和路线距离。
  - 文件：`backend/services/verify_service.py`
  - 验收：手工构造的缺字段、虚假 POI、超预算和重复景点结果会被拒绝并返回具体错误码。
- [x] 增加验证服务单元测试。
  - 文件：新增 `backend/tests/test_verify_service.py`
  - 验收：覆盖成功、本地降级、坐标不符、超预算、远距离路线和重复 POI。

### 0.3 分享、导出与鉴权修复

- [x] 创建分享链接必须要求行程所有者登录。
  - 文件：`backend/api/share.py`
  - 验收：游客和非所有者不能为私有行程生成分享链接。
- [x] 读取分享和导出行程必须校验公开状态、有效分享 token 或所有者身份。
  - 文件：`backend/api/share.py`、`backend/api/itineraries.py`
  - 验收：私有行程 ID 不可被枚举导出；公开行程和有效分享链接可正常访问。
- [x] 将内存 `_share_tokens` 替换为数据库表或 Redis 持久化记录。
  - 文件：`backend/database/models.py`、`backend/api/share.py`、可选 `backend/utils/redis_client.py`
  - 验收：重启后有效分享链接仍可访问，可配置失效时间和撤销。
- [x] 将 JWT 密钥从硅基流动 API Key 派生改为独立 `JWT_SECRET` 配置。
  - 文件：`backend/config.py`、`backend/utils/auth.py`、`.env.example`
  - 验收：未配置生产密钥时启动给出明确告警；更换外部 LLM Key 不会令所有用户 token 失效。
- [x] 为分享与鉴权增加 API 测试。
  - 文件：新增 `backend/tests/test_share_auth.py`
  - 验收：覆盖游客、非所有者、所有者、公开行程、失效 token 五类场景。

### 0.4 Phase 0 完成检查

- [x] 流式请求中收藏加权生效。
- [x] 无高德 Key 时不会出现虚假的 `spots_valid=true`。
- [x] 私有行程无法被未授权查看、分享或导出。
- [x] JWT 不依赖外部 LLM API Key。
- [x] 相关测试通过，或有记录完整的本地 API 验证结果。

---

## Phase 1 - 确定性规划优先

目标：将“评分、预算和路线”从 LLM 降级逻辑升级为正式规划器，建立模型不可修改的事实边界。

### 1.1 拆分规划器

- [x] 从 `model_service.py` 提取 `planner_service.py`。
  - 职责：候选评分、偏好加权、收藏加权、历史负反馈、预算筛选、景点去重、日内路线排序、交通成本估算。
  - 文件：新增 `backend/services/planner_service.py`，修改 `backend/services/model_service.py`
  - 验收：不调用任何 LLM 也可生成完整且结构正确的确定性行程。
- [x] 定义 `PlanningRequest`、`CandidatePoi`、`PlannedItinerary`、`PlanningReason` 等领域模型。
  - 文件：新增 `backend/schemas/planning.py`
  - 验收：接口不再在多个服务间传递无约束的 `dict`。
- [x] 将候选池大小由 `days * 3` 调整为可配置的 `days * 8`，交给规划器筛选。
  - 文件：`backend/services/generation_service.py`、`backend/config.py`
  - 验收：不同偏好和预算下候选不足时有明确降级记录。
- [x] 为规划器编写单元测试和固定基准样例。
  - 文件：新增 `backend/tests/test_planner_service.py`、`backend/tests/fixtures/`
  - 验收：相同输入得到稳定结果；预算、偏好、距离、收藏和去重规则均可验证。

### 1.2 建立事实包与 Schema

- [x] 定义模型可写字段与系统回填字段的响应 Schema。
  - 模型可写：`summary`、`note`、`transport_advice`、`reason`。
  - 系统回填：`poi_id`、名称、坐标、价格、时长、日费用、总费用。
  - 文件：新增 `backend/schemas/itinerary.py`
  - 验收：模型输出不含或篡改事实字段时，最终响应仍完全来自规划器数据。
- [x] 构建最小事实包，只将选定 POI、顺序、距离、预算和用户偏好传给模型。
  - 文件：新增 `backend/services/fact_pack_service.py`
  - 验收：日志中不再出现整城市 POI 列表被发送给模型。
- [x] 实现 JSON Schema 校验、一次修复请求和确定性结果降级。
  - 文件：新增 `backend/services/response_validation_service.py`
  - 验收：模型不合法输出不会直接呈现；修复失败时用户仍收到完整、可用的规划行程。
- [x] 更新行程接口返回元数据：`generation_source`、`validation_status`、`fallback_reason`。
  - 文件：`backend/schemas/generate.py`、前端 API 类型与行程展示组件
  - 验收：开发环境可明确追踪每次结果来源与是否降级。

### 1.3 Phase 1 完成检查

- [x] 任意 LLM 输出都无法修改 POI、费用、坐标、时长和排序事实。
- [x] 模型不可用时，确定性规划器仍能返回通过规则校验的行程。
- [x] 生成结果包含可追溯的来源和验证状态。

---

## Phase 2 - 本地模型与 Provider 路由

目标：以 Ollama 本地模型为默认能力，外部 API 作为明确可观测的受控回退。

### 2.1 统一 Provider 接口

- [x] 定义 `LLMProvider` 协议：`generate_json()`、`stream_chat()`、健康检查和模型标识。
  - 文件：新增 `backend/services/llm_provider.py`
- [x] 实现 `OllamaProvider`。
  - 配置：`OLLAMA_BASE_URL`、`OLLAMA_MODEL`、超时、重试次数。
  - 验收：可通过 `http://localhost:11434` 调用本地 Ollama 模型。
- [x] 将现有硅基流动调用重构为 `OpenAICompatibleProvider`。
  - 文件：修改或替换 `backend/services/llm_service.py`
  - 验收：保留现有外部 API 能力，不再和业务逻辑强耦合。
- [x] 实现 `DisabledProvider`，支持无模型时直接返回确定性结果。
- [x] 通过配置决定默认 Provider、回退 Provider 和启用范围。
  - 文件：`backend/config.py`、`.env.example`
  - 验收：无需修改业务代码即可在 Ollama、外部 API、禁用模式之间切换。

### 2.2 路由、超时与观测

- [x] 为请求定义复杂度规则和路由原因。
  - 示例：多城市、超长天数、复杂偏好、模型修复失败可触发外部模型回退。
  - 文件：新增 `backend/services/model_router.py`
- [x] 为本地模型调用增加健康检查、超时、熔断与请求队列保护。
  - 验收：Ollama 离线或超时不会阻塞 FastAPI 工作进程。
- [x] 记录 `request_id`、Provider、模型版本、耗时、token、成本、回退原因与验证结果。
  - 文件：`backend/utils/logger.py`、相关服务
  - 验收：可按 request_id 排查一次生成的完整路径。
- [x] 调整桌宠聊天的模型路由，默认使用本地模型，必要时回退外部模型。
  - 文件：`backend/api/chat.py`

### 2.3 Phase 2 完成检查

- [x] Ollama 是普通行程和常规聊天的默认 Provider。
- [x] 外部 API 调用有明确原因、脱敏上下文和成本记录。
- [x] 本地模型不可用时系统可自动降级，核心生成不失败。

---

## Phase 3 - 训练数据闭环与本地微调

目标：以真实、可验证、可评测的数据微调模型的格式遵从和表达能力，而不是把实时旅游知识写入模型权重。

### 3.1 数据采集与存储

- [x] 为已保存行程记录模型版本、规划版本、候选 POI 版本、验证结果和回退原因。
  - 文件：`backend/database/models.py`、数据库迁移、`backend/api/itineraries.py`
- [x] 记录用户编辑差异：替换、删除、排序调整、备注修改及最终保存版本。
  - 文件：行程编辑 API、数据模型、前端编辑逻辑
- [x] 记录低评分和验证失败的结构化原因，禁止把单条反馈直接用于在线训练。
  - 文件：新增 `backend/services/quality_log_service.py`、`backend/database/models.py`（TripQualityLog 表）、修改 `backend/api/itineraries.py`
  - 验收：低评分(<=2)和验证失败(overall_valid=false)时写入结构化记录，包含错误码、生成来源、回退原因；不含 PII
- [x] 新增训练样本导出脚本，默认脱敏，按质量标签筛选。
  - 文件：新增 `model/export_training_dataset.py`
  - 验收：支持 SFT/评测/负样本三种导出，按质量标签(gold/silver/fallback/negative)分类，移除 user_id 等敏感字段

### 3.2 黄金数据与评测集

- [ ] 制定人工审核规范：景点真实性、路线合理性、预算、时间安排、可读性和偏好匹配。
  - 文件：新增 `model/ANNOTATION_GUIDE.md`
- [ ] 建立独立的 train/validation/test 划分，按请求和 POI 序列去重。
  - 文件：新增 `model/build_dataset.py`
- [ ] 建立固定离线评测脚本。
  - 指标：Schema 合法率、候选 POI 违规率、业务规则通过率、无需修复率、P95 时延。
  - 文件：新增 `model/evaluate_model.py`
- [ ] 仅在黄金数据和评测集达标后，扩充外部教师模型生成的数据。

### 3.3 SFT 与部署

- [ ] 更新 `MODEL_TRAINING_TODO.md`，使其与“事实包 + 允许字段”协议一致。
- [ ] 新建 LLaMA-Factory SFT 配置和数据集注册说明。
  - 文件：新增 `model/sft_config.yaml`、`model/LLAMA_FACTORY_DATASET.md`
- [ ] 先完成 SFT 训练和离线评测，暂不启动 GSPO。
- [ ] 通过验收后导出模型并创建 Ollama `tripcraft` 模型。
- [ ] 对比通用 Qwen、本地 SFT 模型、外部 API 和确定性降级的质量、时延与成本。
- [ ] GSPO 只有在拥有足够人工/行为偏好对且 SFT 达标后再立项。

### 3.4 Phase 3 完成检查

- [ ] JSON Schema 合法率 >= 99%。
- [ ] 候选 POI 违规引用率 = 0。
- [ ] 预算、路线、时长业务规则通过率 >= 98%。
- [ ] 无需修复率 >= 95%。
- [ ] 测试集和训练集独立，评测报告可复现。

---

## Phase 4 - RAG 与个性化演进

目标：提升长尾检索、动态数据新鲜度和个性化排序质量。

### 4.1 RAG 正确性与新鲜度

- [ ] 修改聊天检索 API，使用户问题作为真实 query 传入 RAG。
  - 文件：`backend/api/chat.py`、`backend/services/rag_service.py`
  - 验收：不同问题在同一城市召回不同且相关的 POI。
- [ ] 为 POI 增加 `source`、`updated_at`、`content_hash`、`confidence` 元数据。
  - 文件：`backend/database/models.py`、迁移、采集服务
- [ ] 索引失效依据从 POI 数量改为版本或内容哈希。
  - 文件：`backend/services/rag_service.py`
- [ ] POI 更新后失效缓存并触发异步索引更新。

### 4.2 Hybrid RAG

- [ ] 评估并接入中文 embedding 模型，保留 TF-IDF/BM25 作为关键字召回。
- [ ] 实现 metadata 过滤与混合重排序：城市、类别、预算、人群、数据新鲜度、评分、距离和偏好。
- [ ] 将 POI 事实、攻略内容与用户评论拆分为独立集合与权限策略。
- [ ] 建立检索离线评测集，统计 Recall@K、MRR、按问题类别分桶的命中率。

### 4.3 动态 POI 与个性化

- [ ] 新城市请求触发高德采集、审核、去重、入库、缓存失效和索引更新。
- [ ] 用户收藏、显式偏好、历史评分和负反馈接入规划器排序特征。
- [ ] 增加“推荐理由”“数据来源/更新时间”“验证状态”的前端展示。
- [ ] 多城市联程单独设计城际交通规划器，禁止直接拼接单城市结果。

### 4.4 Phase 4 完成检查

- [ ] 新城市可在受控采集与审核后进入可生成范围。
- [ ] 语义问题的检索指标优于当前 TF-IDF 基线。
- [ ] 用户能够理解推荐依据、事实来源和验证结果。

---

## 建议开发顺序

1. [x] 完成 0.1：统一生成请求与编排。
2. [x] 完成 0.2：严格事实验证和测试。
3. [x] 完成 0.3：分享、导出、JWT 安全修复。
4. [x] 完成 1.1：规划器拆分及测试。
5. [x] 完成 1.2：事实包、Schema 回填、修复与降级。
6. [x] 完成 2.1-2.2：Ollama Provider、外部回退和观测。
7. [ ] 完成 3.1-3.3：数据闭环、评测、SFT 与 Ollama 部署。
8. [ ] 完成 4.1-4.3：Hybrid RAG、动态 POI 与个性化。

## 变更记录

| 日期 | 阶段 | 结果 | 备注 |
|---|---|---|---|
| 2026-08-12 | 规划 | 已创建 | 基于 AI 架构优化设计拆分待办，尚未开始业务代码改造 |
| 2026-08-12 | Phase 0.1 | 已完成 | 共享 Schema 与编排服务已接入两类接口；3 个后端测试和针对性 TypeScript 检查通过。全量前端构建仍受现有缺失依赖及 `ItineraryTimeline.tsx` 错误阻塞 |
| 2026-08-12 | Phase 0.2 | 已完成 | 高德不可用时改为本地精确匹配；新增结构、POI、重复、费用、预算、路线与来源校验；12 个后端测试和 API 类型检查通过 |
| 2026-08-12 | Phase 0.3 | 已完成 | 分享 Token 哈希持久化并支持过期/撤销；分享和导出增加所有权/公开状态校验；JWT_SECRET 独立配置；26 个后端测试通过 |
| 2026-08-13 | Phase 1.1 | 已完成 | 确定性规划器接管评分、偏好/收藏加权、排除、预算、去重、路线和交通成本；候选池改为可配置的 days * 8；35 个后端测试通过；Docker MySQL/Redis 真实链路生成与验证通过 |
| 2026-08-13 | Phase 1.2 | 已完成 | 建立最小事实包与模型文案 Schema，系统回填全部 POI 事实；支持一次修复和确定性降级；响应及前端展示来源元数据；39 个后端测试、TypeScript 检查和 Vite 生产构建通过；Docker MySQL/Redis 降级链路验证通过 |
| 2026-08-13 | Phase 2.1 | 已完成 | 统一 LLMProvider 协议，实现 Ollama、OpenAI 兼容与禁用 Provider，并支持按配置切换范围；44 个后端测试通过；本机 qwen3.5:9b 健康检查与 JSON Schema 真实调用通过 |
| 2026-08-13 | Phase 2.2 | 已完成 | 增加复杂度路由、外部回退原因、Ollama 超时/并发队列/熔断、请求 ID 与 Provider 观测；聊天默认走本地模型；50 个后端测试和前端生产构建通过；Docker MySQL/Redis + qwen3.5:9b 真实行程与流式聊天调用通过 |
| 2026-08-13 | Phase 3.1（追踪字段） | 已完成 | SavedTrip 增加模型、规划器、POI 版本、来源、验证状态和回退原因；提供幂等增量迁移；52 个后端测试和前端构建通过；Docker MySQL 真实迁移与事务回滚验证通过 |
| 2026-08-13 | Phase 3.1（编辑差异） | 已完成 | 新增行程版本与 trip_edit_events，结构化记录替换、删除、新增、排序和备注变化；前端编辑后同步最终版本；55 个后端测试和前端构建通过；Docker MySQL 建表与事务回滚验证通过 |
| 2026-08-14 | Phase 0.4 | 已完成 | 验证流式请求中收藏加权生效：新增 3 个测试覆盖流式 favorite_poi_ids 传递、规划器收藏评分加权和流式/非流式一致性；59 个后端测试通过。Phase 0 全部完成 |
| 2026-08-14 | Phase 3.1（质量记录） | 已完成 | 新增 TripQualityLog 表和 quality_log_service：低评分(<=2)和验证失败时记录结构化原因（错误码、生成来源、回退原因），不含 PII；接入 rate_trip 和 save_trip；17 个新增测试，76 个后端测试通过 |
| 2026-08-14 | Phase 3.1（导出脚本） | 已完成 | 新增 model/export_training_dataset.py：支持 SFT/评测/负样本三种格式导出，按 gold/silver/fallback/negative 质量标签分类，移除 user_id 等敏感字段，输出 manifest.json |
