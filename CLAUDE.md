# CLAUDE.md

This is the **clean repo** for the token-level GFM classifier project.
Old working directory: `/work/ymj1123ntu/token_level_gfm_classifier` (kept as data stash, not source of truth).

> **跨 session 工作守則(鐵律、模型調度、判斷 rubric)在 `~/.claude/CLAUDE.md` 與 `~/.claude/playbook/`**。本檔只放這個 repo 的結構與指令。

## Environment

- **Nano4**: H200, 免費額度**已耗盡(2026-07)**,`sbatch` 會被 wallet 負值擋下。只有帳號 `MST114550` 能用。shell 輸出可能不可信,關鍵數字交叉驗證。
- **Taiwania-2**: V100 cluster,**續跑訓練的目的地**(交接包見 `taiwania2_continue/`)。原 MetaTransformer 訓練也在此。
- **本地 4090**: real-world / 新基因體泛化評估(純推論,不需 HPC;交接包見 `local_realworld_eval/`)。
- **TWCC (Nano5)**: H100,budget 已於 5/30 耗盡(歷史)。

Python: 跑任何 python 前先 `conda activate gfm`(Miniconda,Python 3.11,PyTorch 2.5.1+cu121)。

## Layout

```
gfm-classifier/
├── configs/            YAML configs for each model
├── scripts/            Training, evaluation, analysis Python scripts
├── slurm/              SLURM batch scripts (env-specific entries inside)
├── docs/               Meeting notes, slide decks, plans
├── envs/<env>/STATUS.md     Per-environment state (paths, budget, progress)
├── data_manifest/      Pointers to big files (not in repo)
├── results_summary/    metrics.json per model (no predictions.npz)
└── small_predictions/  Small .npz / .tsv used by downstream analysis
```

## Key commands

```bash
# Train
python scripts/train.py --config configs/nt_token_genus_v9_50M.yaml

# Evaluate forward-only
python scripts/evaluate.py --config configs/nt_token_genus_v9_50M.yaml

# Evaluate with RC TTA
python scripts/evaluate.py --config configs/nt_token_genus_v9_50M.yaml --rc_tta

# Sample-level eval
python scripts/evaluate_sample.py --predictions <preds.npz> --out_dir <dir> \
    --reads_per_sample 1000 --n_partition_samples 100 \
    --n_sparse_samples 200 --genera_present 50
```

See [`PROGRESS.md`](./PROGRESS.md) for current project state.
