# Silver 样本人工抽检流程

`silver` 不是自动训练数据。它表示没有明确事实矛盾，但仍有未被事实包或交叉证据充分确认的文案声明。当前生产配置采用全自动证据门槛，普通 `silver` 不需要人工审核，也不会进入 SFT。

1. 导出待抽检包。该 JSONL 只含合成请求、事实包、文案、规则验证、裁判结论和公开证据，不含用户信息：

```powershell
python model/export_silver_review_queue.py --output model/training_data/silver_review_queue.jsonl --min-confidence 0.85
```

2. 审核每条的 `narrative` 是否只陈述 `fact_pack` 支持的内容；对于事实包外内容，检查 `evidence` 的来源是否直接支持。任何无法确认或不适合作为模型学习目标的样本都不要批准。

3. 自动放行仅适用于 `auto_gold_candidate`：置信度不低于 0.90、无硬错误、无矛盾、且两个裁判均无未证实声明。运行自动评审时会直接写入 approved 状态；对历史数据可执行回填：

```powershell
python model/auto_approve_training_candidates.py --batch auto-evidence-20260815
```

4. 导出自动批准批次。普通 pending silver、挑战集、负例和任何未闭环证据的样本永远不会进入 SFT：

```powershell
python model/export_approved_auto_labels.py --batch auto-evidence-20260815 --output model/training_data/auto-evidence-20260815.jsonl
```

导出的样本记录原始自动标签和批准来源，训练质量标签为 `gold`。自动审批只依赖证据闭环，不依赖人工审核。
