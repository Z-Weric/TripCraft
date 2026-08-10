# TripCraft 模型训练 TODO

> 基座模型：Qwen2-7B-Instruct
> 硬件：RTX 4060 16G
> 训练方法：QLoRA 4-bit
> 训练框架：LLaMA-Factory
> 两阶段：SFT（监督微调）→ GSPO（偏好优化）

---

## 一、环境准备

### 1.1 Python 版本升级
- [ ] 检查当前 Python 版本（项目用 3.9，LLaMA-Factory 需要 ≥ 3.10）
- [ ] 用 conda 或 pyenv 安装 Python 3.10+
- [ ] 创建新的虚拟环境 `tripcraft-train`
- [ ] 安装基础依赖：torch, transformers, accelerate

### 1.2 安装 LLaMA-Factory
- [ ] `git clone https://github.com/hiyouga/LLaMA-Factory.git`
- [ ] `cd LLaMA-Factory && pip install -e ".[torch,metrics]"`
- [ ] 安装 bitsandbytes（4-bit 量化）：`pip install bitsandbytes`
- [ ] 安装 flash-attn（加速训练）：`pip install flash-attn --no-build-isolation`
- [ ] 验证 GPU 可用：`python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"`

### 1.3 下载基座模型
- [ ] 从 ModelScope 下载 Qwen2-7B-Instruct（国内更快）
- [ ] 模型存放路径：`/models/Qwen2-7B-Instruct`
- [ ] 验证模型可加载

---

## 二、训练数据生成

### 2.1 完整数据生成
- [ ] 运行 `python model/generate_training_data.py`（不加 --quick）
- [ ] 预计产出：
  - SFT 数据：~120 条（`model/training_data/train_sft.json`）
  - GSPO 数据：~150 条（`model/training_data/train_gspo.json`）
- [ ] 耗时：约 2-3 小时

### 2.2 数据格式转换
- [ ] SFT 数据转为 LLaMA-Factory 的 alpaca 格式（已有，确认格式正确）
- [ ] GSPO 数据转为 LLaMA-Factory 的 preference 格式
  ```json
  {"prompt": "...", "chosen": "...", "rejected": "..."}
  ```
- [ ] 数据集注册：在 LLaMA-Factory 的 `data/dataset_info.json` 中注册
  ```json
  "tripcraft_sft": {
    "file_name": "train_sft.json",
    "columns": {"prompt": "instruction", "response": "output"}
  },
  "tripcraft_gspo": {
    "file_name": "train_gspo.json",
    "columns": {"prompt": "prompt", "chosen": "chosen", "rejected": "rejected"}
  }
  ```
- [ ] 复制数据文件到 LaMA-Factory 的 data 目录

### 2.3 数据质量检查
- [ ] 抽检 10 条 SFT 数据，确认 JSON 格式正确、景点真实
- [ ] 抽检 5 条 GSPO 数据，确认 chosen 确实比 rejected 质量好
- [ ] 统计数据分布（城市覆盖、天数分布、预算分布）

---

## 三、阶段一：SFT 监督微调

### 3.1 训练配置
- [ ] 创建 SFT 训练配置 `model/sft_config.yaml`：
  ```yaml
  # 基本配置
  model_name_or_path: /models/Qwen2-7B-Instruct
  stage: sft
  do_train: true
  finetuning_type: lora
  lora_target: q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj
  lora_rank: 8
  lora_alpha: 16

  # 量化
  quantization_bit: 4
  quantization_method: bitsandbytes

  # 数据
  dataset: tripcraft_sft
  template: qwen
  cutoff_len: 2048
  max_samples: 1000

  # 训练参数
  output_dir: /models/tripcraft-sft
  num_train_epochs: 3
  per_device_train_batch_size: 1
  gradient_accumulation_steps: 8
  learning_rate: 5e-5
  warmup_ratio: 0.1
  lr_scheduler_type: cosine
  logging_steps: 10
  save_steps: 50
  bf16: true
  ```

### 3.2 启动 SFT 训练
- [ ] 启动训练：
  ```bash
  cd LLaMA-Factory
  llamafactory-cli train ../model/sft_config.yaml
  ```
- [ ] 监控显存占用（应 < 16G）
- [ ] 监控 loss 下降趋势
- [ ] 预计训练时间：2-4 小时（120 条 × 3 epoch）

### 3.3 SFT 模型测试
- [ ] 合并 LoRA 权重：
  ```bash
  llamafactory-cli export ../model/sft_merge.yaml
  ```
- [ ] 测试生成效果：用测试 prompt 调用模型，检查输出 JSON 格式
- [ ] 对比 SFT 前后效果：是否学会了 TripCraft 行程格式

---

## 四、阶段二：GSPO 偏好优化

### 4.1 训练配置
- [ ] 创建 GSPO 训练配置 `model/gspo_config.yaml`：
  ```yaml
  model_name_or_path: /models/tripcraft-sft  # SFT 模型
  stage: gspo
  do_train: true
  finetuning_type: lora
  lora_target: q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj
  lora_rank: 8
  lora_alpha: 16
  quantization_bit: 4
  quantization_method: bitsandbytes

  dataset: tripcraft_gspo
  template: qwen
  cutoff_len: 2048

  output_dir: /models/tripcraft-gspo
  num_train_epochs: 1
  per_device_train_batch_size: 1
  gradient_accumulation_steps: 8
  learning_rate: 5e-6
  warmup_ratio: 0.1
  logging_steps: 10
  save_steps: 50
  bf16: true
  ```

### 4.2 启动 GSPO 训练
- [ ] 启动训练：
  ```bash
  llamafactory-cli train ../model/gspo_config.yaml
  ```
- [ ] 监控显存（GSPO 比 SFT 更吃显存，注意 OOM）
- [ ] 如果 OOM：减小 `cutoff_len` 到 1024 或减少 `lora_rank` 到 4
- [ ] 监控 reward 上升趋势
- [ ] 预计训练时间：1-2 小时（150 条 × 1 epoch）

### 4.3 GSPO 模型测试
- [ ] 合并 LoRA 权重
- [ ] 对比 SFT 和 GSPO 输出质量
- [ ] 验证：GSPO 后的模型是否更倾向生成验证通过的行程

---

## 五、模型部署

### 5.1 安装 Ollama
- [ ] 下载安装 Ollama：https://ollama.com
- [ ] 将合并后的模型转为 GGUF 格式：
  ```bash
  python convert.py /models/tripcraft-gspo --outtype f16
  ```
- [ ] 创建 Ollama 模型：
  ```bash
  ollama create tripcraft -f Modelfile
  ```

### 5.2 后端接入
- [ ] 更新 `backend/services/llm_service.py`：
  - API 地址改为 `http://localhost:11434/api/chat`
  - 模型名改为 `tripcraft`
  - 请求格式改为 Ollama 兼容
- [ ] 更新 `backend/config.py`：
  - `llm_api_base` 改为 Ollama 地址
  - `llm_model` 改为 `tripcraft`
- [ ] 测试本地模型生成行程

### 5.3 效果对比
- [ ] 对比三个版本的生成质量：
  1. 原始 LongCat-2.0（远程 API）
  2. SFT 微调后（本地）
  3. GSPO 优化后（本地）
- [ ] 对比指标：
  - 行程 JSON 格式正确率
  - 验证通过率（景点真实/预算合规/路线合理）
  - 生成速度（本地 vs 远程）
  - 行程质量（评分优先/路线就近/时段合理）

---

## 六、时间线

| 阶段 | 内容 | 预计时间 | 依赖 |
|---|---|---|---|
| 一 | 环境准备 | 2 小时 | 无 |
| 二 | 数据生成 | 2-3 小时 | 无（可和一并行） |
| 三 | SFT 训练 | 4-6 小时 | 一 + 二 |
| 四 | GSPO 训练 | 2-3 小时 | 三 |
| 五 | 部署接入 | 2 小时 | 四 |
| **总计** | | **12-16 小时** | |

---

## 七、风险与降级

| 风险 | 降级方案 |
|---|---|
| Python 3.9 不兼容 LLaMA-Factory | 用 unsloth 替代，或升级 Python |
| 16G 显存 OOM | 减小 cutoff_len / lora_rank / 用 8-bit 代替 4-bit |
| SFT 训练 loss 不下降 | 检查数据格式、增大 learning_rate、增加 epoch |
| GSPO 训练 OOM | 跳过 GSPO，只用 SFT |
| Ollama 不支持 Qwen2 | 用 vLLM 部署，或转 ONNX 格式 |
| 训练数据不足 | 用 mock 增加生成量，或数据增强（同义改写 prompt） |

---

## 八、验收标准

- [ ] SFT 模型能直接输出合法 JSON 行程（不需要清理 markdown 标记）
- [ ] SFT 模型生成的行程验证通过率 ≥ 80%
- [ ] GSPO 模型生成的行程质量优于 SFT（路线更合理/评分更高）
- [ ] 本地模型生成速度 < 10 秒（vs 远程 API 30-40 秒）
- [ ] 后端成功切换到本地模型，功能正常