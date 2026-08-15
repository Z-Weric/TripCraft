# TripCraft LLaMA-Factory SFT

TripCraft fine-tunes narrative formatting and wording only. POI selection, routes,
costs, time slots, coordinates, and ordering remain planner-owned facts. Do not train
the model to produce or revise these fields.

## Preconditions

1. Use Python 3.10 or newer in a separate training environment.
2. Install a current LLaMA-Factory release with CUDA-compatible PyTorch.
3. Export approved samples, deduplicate and split them, then prepare only the train split.
4. Keep `validation.jsonl` and `test.jsonl` immutable. `test.jsonl` is never copied into
   LLaMA-Factory or used to select checkpoints.

```powershell
python model/export_training_dataset.py --output model/training_data/exported --format all
python model/build_dataset.py --input model/training_data/exported/sft_samples.jsonl --output model/training_data/splits
python model/prepare_sft_dataset.py --input model/training_data/splits/train.jsonl --output model/training_data/tripcraft_sft_train.json
```

The preparation step accepts only `gold` records by default. Add `--quality-labels gold,silver`
only after documented review approval. It produces Alpaca-format records with an immutable fact
pack in `instruction` and the allow-listed narrative JSON in `output`.

## Register the dataset

Copy `model/training_data/tripcraft_sft_train.json` into the LLaMA-Factory `data` directory.
Add this entry to that installation's `data/dataset_info.json`:

```json
"tripcraft_sft_train": {
  "file_name": "tripcraft_sft_train.json",
  "formatting": "alpaca",
  "columns": {
    "prompt": "instruction",
    "query": "input",
    "response": "output"
  }
}
```

Set `dataset_dir` and `model_name_or_path` in `model/sft_config.yaml` to absolute paths on the
training machine. Start a first run only after the gate below is met:

```powershell
llamafactory-cli train E:\AI-project\TripCraft\model\sft_config.yaml
```

## Validation Gate

Do not start SFT until the fixed validation/test data satisfies the annotation guide and has enough
reviewed gold examples to represent requested destinations, days, budgets, and preferences. Run
offline evaluation for every candidate checkpoint. The acceptance thresholds are:

- Schema valid rate >= 99%
- Allow-listed POI violation rate = 0
- Business rule pass rate >= 98%
- No-repair rate >= 95%

Predictions must be emitted as JSONL with `id`, `narrative` (or `output`), `latency_ms`,
`validation_status`, and `repair_attempted`, then evaluated without external map calls:

```powershell
python model/evaluate_model.py --test model/training_data/splits/test.jsonl --predictions predictions.jsonl --output evaluation.json
```

SFT is the only approved training stage now. GSPO requires a separate proposal backed by sufficient
human-reviewed preference pairs and an SFT model that passes the complete validation gate.
