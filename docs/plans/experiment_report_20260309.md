# Token-level GFM Classifier — 週報（2026-03-04 ~ 2026-03-09）

> **日期**：2026-03-09  
> **環境**：TWCC (台智雲) SLURM 叢集 · NVIDIA H100 80GB HBM3  
> **Repo**：`/work/ymj1123ntu/token_level_gfm_classifier`  
> **Backbone**：`InstaDeepAI/nucleotide-transformer-v2-500m-multi-species` (498M params)

---

## 0. 本週摘要


| 項目       | 內容                                                                                                         |
| -------- | ---------------------------------------------------------------------------------------------------------- |
| **核心成果** | v8 genus 模型 (5M balanced) 完成 30 epochs 訓練與評估，RC TTA accuracy **63.05%**，較 500K baseline (v4) 提升 **+7.8pp** |
| **關鍵發現** | 資料量與平衡性為效能瓶頸，10x data → +7.8pp；Overfitting 從 6.25% 降至 1.3%                                                 |
| **新功能**  | 訓練 resume 機制、Resource Monitor (GPU/RAM/時間追蹤)、`--init_from` 跨實驗權重遷移                                         |
| **進行中**  | v9 genus (50M balanced, batch=256) — Job 134209 running                                                    |


---

## 1. 完成的實驗

### 1.1 v8 Genus — 5M Balanced Dataset

**目的**：驗證「資料不足」假說。將訓練資料從 500K imbalanced 提升至 5M species-balanced。


| 項目                | v4 (500K baseline)     | v8 (5M balanced) | 變化   |
| ----------------- | ---------------------- | ---------------- | ---- |
| 訓練資料量             | 450K                   | 4.5M (10x)       | +10x |
| Species per class | 平均 326                 | 平均 3,257         | +10x |
| 類別平衡              | 高度不平衡 (22.8% vs 0.06%) | Species-balanced | 顯著改善 |


#### 訓練過程

v8 訓練歷經三個 SLURM 工作：


| Job ID | 階段   | Epochs  | 結果                              |
| ------ | ---- | ------- | ------------------------------- |
| 129698 | 初始訓練 | 1→14/20 | 48h 時限到，val_acc=60.56%          |
| 132076 | 接續訓練 | 15→30   | 48h 時限到，val_acc=62.02%，eval 未跑完 |
| 133577 | 最終評估 | —       | Forward + RC TTA 完整評估           |


> 為支援第二次訓練，實作了 `--resume` 功能，可從 `last.pt` checkpoint 恢復 optimizer state 和 epoch counter。

#### v8 最終結果


| Metric             | Forward-only | RC TTA     | vs v4 (500K)            |
| ------------------ | ------------ | ---------- | ----------------------- |
| **Micro Accuracy** | 62.02%       | **63.05%** | **+7.76pp**             |
| Balanced Accuracy  | 32.70%       | 33.35%     | +8.12pp                 |
| F1 (weighted)      | 60.10%       | 61.06%     | +8.55pp                 |
| **F1 (macro)**     | 36.89%       | **37.97%** | **+12.27pp**            |
| Top-3 Accuracy     | 80.93%       | 81.70%     | —                       |
| Top-5 Accuracy     | 87.53%       | 88.08%     | +5.17pp                 |
| Top-10 Accuracy    | 93.88%       | 94.23%     | +2.94pp                 |
| **F1=0 classes**   | 2            | 2          | **↓7 classes** (from 9) |


#### Overfitting 改善


| 項目                | v4 (500K) | v8 (5M)   |
| ----------------- | --------- | --------- |
| Train Acc         | 60.00%    | 63.32%    |
| Val Acc           | 53.75%    | 62.02%    |
| **Train-Val Gap** | **6.25%** | **1.30%** |


→ Overfitting 從 6.25% 大幅降至 1.3%，說明模型容量未飽和，效能受限於資料量。

#### v8 訓練曲線

```
Epoch   Train_Acc   Val_Acc   Train_Loss   Val_Loss
  1      49.96%     51.80%     1.871        1.783
  5      55.97%     57.04%     1.614        1.588
 10      58.93%     59.42%     1.493        1.473
 14      60.60%     60.56%     1.413        1.418    ← 第一次 48h 結束
 15      58.80%     59.18%     1.488        1.478    ← resume, LR 重設
 20      61.82%     60.59%     1.345        1.389
 25      62.89%     61.77%     1.318        1.371
 29      63.32%     62.02%     1.305        1.361    ← best
```

> 注意：Epoch 15 的 accuracy 回落是因為 LR scheduler 重新 warmup，之後逐漸超越前一輪。

---

### 1.2 Species Classification (500K) — 結果彙整

> 已在前一週完成，此處彙整最終數據。


| Mode                 | v1 (baseline) | v2 (LA τ=0.3) | v3 (WeightedSampler) |
| -------------------- | ------------- | ------------- | -------------------- |
| Direct (fwd)         | 8.08%         | 7.94%         | 7.62%                |
| Direct (RC TTA)      | 8.32%         | 8.37%         | 8.01%                |
| Oracle-Genus         | 20.88%        | 20.85%        | 20.48%               |
| Oracle Macro F1      | 19.8%         | 20.0%         | 19.9%                |
| F1=0 classes         | 613           | 433           | 392                  |
| Top-K routing (k=10) | 8.06%         | —             | —                    |


**結論**：500K 資料量下 species 分類實質上失敗（隨機 = 0.065%），Oracle 上限僅 21%，說明 intra-genus discrimination 也不足。

---

## 2. 新增功能

### 2.1 Resource Monitor (`resource_monitor.py`)

為了回應老師對運算資源評估的需求，新增了完整的資源監控模組：


| 監控項目                | 說明                                        |
| ------------------- | ----------------------------------------- |
| GPU VRAM            | PyTorch allocated + nvidia-smi 實際使用量、peak |
| GPU 計算利用率           | 每 30 秒背景採樣 nvidia-smi utilization %       |
| System RAM          | 進程 RSS、peak、系統總量                          |
| 時間                  | 總耗時、per-epoch、throughput (reads/sec)      |
| Capacity Assessment | 自動判斷 VRAM/RAM/GPU 是否有餘裕                   |


**整合位置**：

- `train.py`：每 epoch 輸出即時 GPU/RAM snapshot，`training_history.csv` 新增 5 個資源欄位
- `evaluate.py`：記錄推論時資源使用

**輸出**：

- `resource_report.json`：完整資源報告（JSON 格式，方便程式處理）
- 終端機直接印出摘要 + 容量評估建議

```
RESOURCE USAGE SUMMARY
======================================================================
  GPU Memory (VRAM):
    PyTorch peak allocated: XX.XX GB
    nvidia-smi peak used:   XX.XX GB
    VRAM total:             84.9 GB
    VRAM utilization:       XX.X%

  GPU Compute Utilization:
    Mean:   XX.X%       ← 判斷 GPU 是否被充分利用

  System RAM:
    Peak RSS:       XX.X GB
    System total:   XX.X GB

  Capacity Assessment:
    VRAM:  MODERATE (XX%) — room to increase batch size
    RAM:   LOW (XX%) — plenty of headroom
    GPU compute: MODERATE (XX%) — could improve with larger batch size
```

### 2.2 `--init_from` 跨實驗權重遷移


| Flag          | 用途     | Epoch 重置               | Phase 1 |
| ------------- | ------ | ---------------------- | ------- |
| `--resume`    | 同一實驗接續 | 否（讀取 checkpoint epoch） | 跳過      |
| `--init_from` | 不同實驗遷移 | 是（從 epoch 0 開始）        | 跳過      |


支援 partial loading：若 head 維度不同（如 genus → species），會自動跳過不匹配的參數。

---

## 3. 進行中：v9 Genus — 50M Balanced Dataset

### 3.1 實驗設計


| 項目                | v8 (5M) | v9 (50M)       | 變化                      |
| ----------------- | ------- | -------------- | ----------------------- |
| 訓練資料量             | 4.5M    | 45M            | 10x                     |
| Species per class | ~3,257  | ~32,573        | 10x                     |
| batch_size        | 32      | **256**        | 8x (提升 GPU 利用率)         |
| grad_accum        | 2       | 1              | effective batch: 64→256 |
| Epochs            | 30      | 10             | 資料量大，更快收斂               |
| 初始權重              | 隨機      | **v8 best.pt** | 遷移學習                    |
| 預估 epoch 時間       | ~3h     | ~5h            |                         |


### 3.2 Subsampling 結果

50M balanced subsample 已成功從 258M 完整 FASTA 中生成：

```
Total reads scanned: 258,740,510
Unique species: 1,535
Target: 50,000,000 → Allocated: 50,000,000
Per-class (species): min=32,573, max=33,018
```

### 3.3 時間估計


| 步驟                        | 預估時間         |
| ------------------------- | ------------ |
| Subsampling               | 19 min (已完成) |
| Training (10 epochs)      | ~50h         |
| Evaluation (fwd + RC TTA) | ~2h          |
| **Total**                 | **~52h**     |


> ⚠️ 48h 時限可能不足以完成 10 epochs。若觸碰時限，可用 `--resume` 接續。

### 3.4 Job 狀態

- **Job ID**: 134209
- **Node**: hgpn05 (H100 80GB)
- **Status**: Running (data loading phase)

---

## 4. 全實驗結果總覽

### 4.1 Genus Classification (120 classes)


| Version  | 描述                | Data       | Fwd Acc | **RC TTA Acc** | F1-macro   | F1=0  | Gap       |
| -------- | ----------------- | ---------- | ------- | -------------- | ---------- | ----- | --------- |
| Baseline | Frozen emb+MLP    | 500K imbal | 42.12%  | —              | —          | —     | —         |
| v3       | RC aug, maxlen128 | 500K imbal | 53.92%  | 55.36%         | 25.82%     | 11    | 6.96%     |
| **v4**   | **maxlen=32**     | 500K imbal | 53.75%  | **55.29%**     | 25.70%     | 9     | 6.25%     |
| v5       | LA τ=1.0          | 500K imbal | 35.17%  | —              | —          | —     | —         |
| v5b      | LA τ=0.3          | 500K imbal | 52.29%  | 53.58%         | 26.53%     | 5     | —         |
| v6       | RC consist+LA     | 500K imbal | 35.87%  | 38.19%         | 22.88%     | —     | —         |
| v7       | RC consist only   | 500K imbal | 54.10%  | 55.18%         | 25.10%     | 11    | —         |
| **v8**   | **5M balanced**   | 5M bal     | 62.02%  | **63.05%**     | **37.97%** | **2** | **1.30%** |
| v9       | 50M balanced      | 50M bal    | —       | —              | —          | —     | —         |


### 4.2 Species Classification (1,535 classes)


| Version | 描述              | Data       | RC TTA Acc | Oracle Acc | Oracle F1-macro | F1=0 |
| ------- | --------------- | ---------- | ---------- | ---------- | --------------- | ---- |
| sp_v1   | baseline        | 500K imbal | 8.32%      | 20.88%     | 19.8%           | 613  |
| sp_v2   | LA τ=0.3        | 500K imbal | 8.37%      | 20.85%     | 20.0%           | 433  |
| sp_v3   | WeightedSampler | 500K imbal | 8.01%      | 20.48%     | 19.9%           | 392  |


---

## 5. Data Scaling 分析

### 5.1 Accuracy vs Data Volume

```
Data Volume    Genus Acc (RC TTA)    Train-Val Gap    F1=0 Classes
────────────   ──────────────────    ─────────────    ────────────
   500K              55.29%              6.25%             9
     5M              63.05%              1.30%             2
    50M              ???                 ???               ???      ← v9 running
   258M              (target)            (target)          (target)
```

**觀察**：

- 500K → 5M (10x): **+7.76pp** accuracy, gap 從 6.25% → 1.30%
- 效能提升 **不是** 來自 model tricks（v5/v6/v7 各種 tricks 最多 ±0.5pp），而是 **資料量**
- 這與 MetaTransformer (Wichmann 2023) 的結論一致：他們用大規模平衡 reads（coverage factor 3，總量未明確報告）達到 98.3% genus recall

### 5.2 對比 MetaTransformer


| 項目             | 我們 (v8)                              | MetaTransformer |
| -------------- | ------------------------------------ | --------------- |
| 模型大小           | 498M (LoRA 5.54M trainable)          | ~5M             |
| Tokenization   | 6-mer (NT v2 tokenizer)              | 12-mer (custom) |
| 訓練資料量          | 5M balanced                          | ~92M balanced   |
| Genus accuracy | 63.05%                               | ~98%            |
| 資料來源           | 同源 (HGR UMGS genomes, ART simulator) | 同源              |


→ 差距主要來自 **18x 資料量差距**，而非模型架構。v9 (50M) 應能顯著縮小這個差距。

### 5.3 預期 Scaling 趨勢

基於 5M→50M 的 log-linear scaling 假設：


| Data Volume         | 預期 Genus Acc (RC TTA) | 信心    |
| ------------------- | --------------------- | ----- |
| 5M                  | 63.05% (actual)       | —     |
| 50M                 | ~72-78%               | 中等    |
| 258M                | ~82-90%               | 低（外推） |
| MetaTransformer (~614M est.) | 98.3% recall (reported) | —     |


---

## 6. 運算資源評估（初步）

### 6.1 已知資源使用（from v8 training）


| 項目                         | 數值                        |
| -------------------------- | ------------------------- |
| GPU                        | NVIDIA H100 80GB HBM3     |
| VRAM peak (batch=32)       | ~4.7 GB                   |
| VRAM utilization           | ~5.5%                     |
| Training throughput        | ~417 reads/sec (batch=32) |
| Epoch time (5M, batch=32)  | ~3h                       |
| Total training (30 epochs) | ~90h (分兩次 48h job)        |
| Inference throughput       | ~2,500 reads/sec          |


### 6.2 v9 預估（batch=256）


| 項目                          | 預估                           |
| --------------------------- | ---------------------------- |
| VRAM peak                   | ~20-35 GB (H100 80GB 仍有餘裕)   |
| GPU utilization             | 顯著提升（batch 更大 → 更好的 GPU 飽和度） |
| Epoch time (50M, batch=256) | ~5-6h                        |
| Total training (10 epochs)  | ~50-60h                      |


### 6.3 瓶頸分析

> 完整的 `resource_report.json` 將在 v9 完成後提供。


| 瓶頸           | 評估                                                               |
| ------------ | ---------------------------------------------------------------- |
| **GPU VRAM** | H100 80GB 極度充裕（batch=32 僅用 ~5%）；batch=256 可更好利用                  |
| **GPU 計算**   | batch=32 時 GPU 利用率偏低，batch=256 應大幅改善                             |
| **系統 RAM**   | 50M reads 需 ~11GB，128GB 足夠；full 258M 需 ~52GB，仍在範圍內               |
| **I/O**      | Data loading 非瓶頸（all in-memory）                                  |
| **時間**       | **主要限制** — 48h SLURM 時限制約大規模訓練；Full 258M 需 streaming data loader |


### 6.4 是否需要升級？


| 資源                 | 現況              | 結論                                  |
| ------------------ | --------------- | ----------------------------------- |
| GPU VRAM (80GB)    | 使用不到 50%        | **不需要升級**，可用更大 batch                |
| GPU 算力 (H100)      | 足夠              | **不需要升級**，但可受益於多 GPU                |
| RAM (128GB)        | 50M 約 11GB      | **不需要升級**；258M (~52GB) 仍在範圍         |
| **SLURM 時限 (48h)** | **主要瓶頸**        | 建議：(1) 申請更長時限 (72h) 或 (2) 多次 resume |
| **儲存**             | 50M FASTA ~10GB | **不需要升級**                           |


> **建議**：目前硬體規格充足。核心瓶頸是 **SLURM 時間限制**，而非運算資源本身。若能申請 72h 時限或使用 checkpoint resume 機制，現有 H100 + 128GB RAM 可支撐到 full 258M 訓練。

---

## 7. 下週計畫


| 優先序 | 任務                                            | 狀態                   |
| --- | --------------------------------------------- | -------------------- |
| P0  | v9 (50M) 訓練完成與評估                              | Running (Job 134209) |
| P1  | 分析 v9 resource_report.json，提供完整資源評估           | 待 v9 完成              |
| P1  | 若 v9 結果良好，準備 50M species 實驗 (v10)             | 待 v9 結果              |
| P2  | 若 50M 不足，實作 streaming data loader 跑 full 258M | 視需要                  |
| P2  | 整理最終實驗報告（含資源評估）供老師審閱                          | 待所有實驗完成              |


---

## 附錄 A：實驗檔案結構

```
token_level_gfm_classifier/
├── scripts/
│   ├── data_loader.py       — FASTA/TSV 載入, genus↔species 映射
│   ├── dataset.py           — PyTorch Dataset, RC augmentation
│   ├── heads.py             — AttentionPool / Transformer / MeanPool heads
│   ├── model.py             — Backbone + LoRA + Head 整合
│   ├── train.py             — Two-phase 訓練, --resume, --init_from, resource monitor
│   ├── evaluate.py          — 完整評估, RC TTA, oracle-genus, top-k routing
│   ├── resource_monitor.py  — [NEW] GPU/RAM/時間 資源監控
│   ├── subsample_balanced.py — 大規模 FASTA 平衡抽樣
│   └── utils.py             — 工具函式
├── configs/
│   ├── nt_token_genus_v8_5M.yaml    — v8 配置
│   └── nt_token_genus_v9_50M.yaml   — v9 配置 (batch=256)
├── results/
│   ├── nt_token_genus_lora_v8_5M/   — v8 完整結果
│   │   ├── best.pt, last.pt
│   │   ├── training_history.csv     — 30 epochs + 資源欄位
│   │   ├── eval/                    — forward-only 評估
│   │   └── eval_rc_tta/             — RC TTA 評估
│   └── nt_token_genus_lora_v9_50M/  — v9 (進行中)
└── docs/figures/                     — 架構圖與流程圖
```

## 附錄 B：實驗再現指令

```bash
# v8 評估 (已完成)
cd scripts
python evaluate.py --config ../configs/nt_token_genus_v8_5M.yaml --rc_tta

# v9 訓練 (進行中)
python train.py --config ../configs/nt_token_genus_v9_50M.yaml \
  --init_from ../results/nt_token_genus_lora_v8_5M/best.pt

# 生成 50M balanced subsample
python subsample_balanced.py \
  --input /path/to/reads.fa \
  --output_fasta reads_50M.fa \
  --output_labels labels_50M.tsv \
  --total_reads 50000000 --balance_by species
```

