# TripCraft 本地模型训练待办

> 目标：微调模型的 JSON 格式遵从和旅行文案表达。实时 POI 知识、路线、价格、坐标、时长和排序始终由后端规划器与 RAG 提供，不写入模型权重。
>
> 当前状态：已完成数据导出、人工审核规范、去重切分和离线评测工具；尚未满足训练数据与离线验收门槛，因此不启动 SFT 或 GSPO。

---

## 一、不可变协议

- [x] 规划器生成并持有事实包：目的地、预算、偏好、POI、时间、路线、坐标、费用与时长。
- [x] 模型只可输出 `summary`、`transport_advice`、`note`、`reason`，并必须原样引用事实包中的 `day` 与 `poi_id`。
- [x] 后端使用 JSON Schema、POI 顺序校验和业务规则校验；失败时只允许一次修复，之后返回确定性规划结果。
- [ ] 训练、日志和外部教师请求中不得包含 user_id、邮箱、电话、住址或自由文本中的个人信息。

训练目标 JSON：

```json
{
  "summary": "string",
  "days": [{"day": 1, "transport_advice": "string", "items": [{"poi_id": 1, "note": "string", "reason": "string"}]}]
}
```

禁止让 SFT 标签包含或改写 `spot`、`lat`、`lng`、`cost`、`duration`、日费用、总费用或 POI 排序。

---

## 二、数据准备与审核

- [x] 从 SavedTrip 与质量日志导出脱敏的 SFT、评测和负样本。
- [x] 人工审核规范见 [model/ANNOTATION_GUIDE.md](model/ANNOTATION_GUIDE.md)。
- [x] 通过请求指纹和有序 POI 序列去重，生成独立 train/validation/test 切分。
- [x] 新增 `prepare_sft_dataset.py`，把完整行程转为“事实包输入 + 仅文案输出”的 LLaMA-Factory Alpaca 数据。
- [x] 新增受限训练样本审核池：两名审核员一致才自动定稿；分歧必须由第三名审核员裁决。
- [ ] 两名审核员完成 gold 样本复核，覆盖主要城市、天数、预算和偏好组合。
- [ ] 固定 `test.jsonl` 后禁止回流训练或用于手工调参。

```powershell
python model/export_training_dataset.py --output model/training_data/exported --format all
python model/build_dataset.py --input model/training_data/exported/sft_samples.jsonl --output model/training_data/splits
python model/prepare_sft_dataset.py --input model/training_data/splits/train.jsonl --output model/training_data/tripcraft_sft_train.json
```

默认仅转换 `gold` 样本。审核批准后才可显式传入 `--quality-labels gold,silver`。

在 `backend/.env` 配置审核账号后，登录该账号并访问 `/training-review`：

```dotenv
TRAINING_REVIEWER_EMAILS=reviewer-a@example.com,reviewer-b@example.com,reviewer-c@example.com
```

该白名单未配置时，审核 API 会拒绝所有访问。审核页面不会暴露行程所属用户，也不接收自由文本备注；只保存结构化维度、错误码和内部审核账号 ID。

### 自动候选数据任务

自动任务只写入独立的 `training_*` 表，不会创建 `SavedTrip` 或影响线上用户行程。先生成小规模场景，再调用已启动的本地生成接口：

```powershell
python model/generate_benchmark_cases.py --output model/training_data/benchmark_cases.jsonl --max-cases 100 --include-challenges
python model/run_generation_benchmark.py --input model/training_data/benchmark_cases.jsonl --output model/training_data/generation_runs.jsonl --persist
```

先使用人工基准集校准自动裁判。完成校准并确认两个独立裁判 Provider 可用后，才在 `backend/.env` 启用：

```dotenv
AUTO_EVAL_ENABLED=true
AUTO_EVAL_JUDGE_PROVIDERS=ollama,judge_a
AUTO_EVAL_JUDGE_A_API_BASE=https://your-judge-provider.example/v1/chat/completions
AUTO_EVAL_JUDGE_A_API_KEY=your-judge-key
AUTO_EVAL_JUDGE_A_MODEL=your-judge-model
```

随后执行：

```powershell
python model/auto_label_training_samples.py --output model/training_data/auto_labels.jsonl
```

`auto_gold_candidate` 仍需按抽检与校准批次批准，不能直接用于 SFT。

批准经过校准复核的普通矩阵样本，并导出到既有切分和 SFT 转换链路：

```powershell
python model/approve_auto_label_batch.py --batch auto-20260815-calibrated --approve
python model/export_approved_auto_labels.py --batch auto-20260815-calibrated --output model/training_data/approved_auto.jsonl
python model/build_dataset.py --input model/training_data/approved_auto.jsonl --output model/training_data/approved_splits
python model/prepare_sft_dataset.py --input model/training_data/approved_splits/train.jsonl --output model/training_data/tripcraft_sft_train.json
```

外部教师模型不能同时作为裁判。若它是当前生成模型，`AUTO_EVAL_JUDGE_PROVIDERS` 必须配置两个不同于该教师的模型，例如 `ollama,judge_a`；只有一个独立裁判时，结果会保留为 `silver`，不会成为自动高置信候选。

---

## 三、SFT 环境与训练

- [ ] 准备独立的 Python 3.10+ 训练环境与 CUDA 对应的 PyTorch；不改动后端运行环境。
- [ ] 安装当前 LLaMA-Factory 与 4-bit QLoRA 依赖，验证 GPU 与 `bitsandbytes` 可用。
- [ ] 选择与线上 Ollama 兼容的 Qwen Instruct 基座模型，并记录版本和许可证。
- [x] 提供 [model/sft_config.yaml](model/sft_config.yaml) 和 [model/LLAMA_FACTORY_DATASET.md](model/LLAMA_FACTORY_DATASET.md)。
- [ ] 将转换后的训练 JSON 复制到 LLaMA-Factory 数据目录，并注册 `tripcraft_sft_train`。
- [ ] 在评测门槛通过后执行 SFT；记录基座模型、数据 manifest、配置哈希、训练日志与 LoRA 输出路径。

```powershell
llamafactory-cli train E:\AI-project\TripCraft\model\sft_config.yaml
```

根据显存调整 `cutoff_len`、batch size 与梯度累积。先从小样本 smoke run 开始，确认输出严格符合协议后再训练完整数据。

---

## 四、离线评测与上线门槛

- [x] 离线评测脚本统计 Schema 合法率、候选 POI 违规率、业务规则通过率、无需修复率、P95 时延，且不调用外部地图 API。
- [ ] 每个候选 checkpoint 在固定 validation/test 集上执行评测，保存原始预测 JSONL 与报告。
- [ ] Schema 合法率 >= 99%。
- [ ] 候选 POI 违规引用率 = 0。
- [ ] 预算、路线、时长业务规则通过率 >= 98%。
- [ ] 无需修复率 >= 95%。
- [ ] 与通用 Qwen、本地 SFT、外部 API 和确定性降级比较质量、P95 时延与成本。

```powershell
python model/evaluate_model.py --test model/training_data/splits/test.jsonl --predictions predictions.jsonl --output evaluation.json
```

未达标的模型不得替换线上默认 Ollama 模型；系统继续使用现有 Provider 路由与确定性降级。

---

## 五、部署与后续

- [ ] 合并通过验收的 LoRA，转换为 Ollama 可导入格式并创建版本化模型，例如 `tripcraft:sft-YYYYMMDD`。
- [ ] 先在 staging 将 `OLLAMA_MODEL` 指向新标签，完成真实生成、流式聊天、超时和降级回归测试。
- [ ] 记录上线模型版本，支持通过配置立即回滚至通用 Qwen 或 `disabled` Provider。
- [ ] GSPO 仅在 SFT 达标、存在足够人工审核的偏好对、且有单独实验方案时再立项；当前不执行 GSPO。
