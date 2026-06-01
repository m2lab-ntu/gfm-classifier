# MetaTransformer 50M 資料集訓練指令 — Taiwania-2 Agent 用

> **目標**：在 Taiwania-2 上用我們的 50M balanced dataset 訓練原版 MetaTransformer（Wichmann 2023），
> 產出 genus 和 species 兩個模型的分類準確率，與我們的 Token-level GFM Classifier 做 apples-to-apples 比較。

---

## 1. 背景

我們已在 TWCC（H100 GPU）上用 **Nucleotide Transformer v2 + LoRA** 訓練了 genus 和 species 分類模型，使用的是 50M balanced reads（150bp，來自 2,505 HGR-UMGS genomes）。現在要在 **Taiwania-2** 用完全相同的資料集訓練原版 MetaTransformer，做公平比較。

**我們的模型目前的結果（供比較）**：
- Genus (381 classes): ~66% accuracy (50M data, v9 model)
- Species (2,505 classes): ~17% accuracy (50M data, sp_v4 model)

**MetaTransformer 論文原始結果**（Wichmann 2023, 用 full HGR-UMGS 資料集）：
- Genus (120 classes): 98.9% Precision, 98.3% Recall (val)
- Species (2,505 classes): ~93% (val)

---

## 2. 資料描述

### 2.1 需要傳到 Taiwania-2 的檔案

| 檔案 | 大小 | 說明 |
|------|------|------|
| `reads_50M.fa` | 9.0 GB | FASTA，50,000,000 條 150bp reads |
| `labels_50M.tsv` | 3.7 GB | TSV，含 species/genus 標籤 |

這兩個檔案位於 TWCC 的 `/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/`

### 2.2 FASTA Header 格式

```
>lbl|{species_class}|{species_name}|{genus_class}|{genus_name}-{read_id}/{pair}
```

範例：
```
>lbl|397|UMGS1075|34|Collinsella-225/1
CCGCCGTGTCGGTTGTCGGCAAGGACGAGTACGGAGACAAGATGAGAGAGGCGCTGGCCGC...
>lbl|155|GCF_000155515|64|Lactobacillus-154852/2
GCAACTGGTCCAAACAACTCGGTACGATAAGCCGGATTGTCCTGATCAATGTCAGTCAAAA...
```

**關鍵**：MetaTransformer 的 `LabelTransform` 會用 `header.split("|")[class_indices]` 取 label：
- **Species**: `class_indices: 1` → 取到 `397`（species 的 integer class ID）
- **Genus**: `class_indices: 3` → 取到 `34`（genus 的 integer class ID）

所以 **FASTA 不需要改格式**，只要在 config 中設定正確的 `class_indices` 即可。

### 2.3 Labels TSV 格式（僅供參考/驗證用）

```
idx	seq_id	species_class	genus_class	genus_name	species_name
0	lbl|397|UMGS1075|34|Collinsella-225/1	397	34	Collinsella	UMGS1075
1	lbl|155|GCF_000155515|64|Lactobacillus-154852/2	155	64	Lactobacillus	GCF_000155515
```

### 2.4 類別數量

| 任務 | 類別數 | class_indices |
|------|--------|---------------|
| Genus | **381** | **3** |
| Species | **2,505** | **1** |

---

## 3. Step 1: 資料傳輸

從 TWCC 傳到 Taiwania-2（在 Taiwania-2 上執行）：

```bash
# 建立目標目錄
mkdir -p /work/ymj1123ntu/data_50M

# 從 TWCC scp（需要替換 TWCC 的 hostname）
scp ymj1123ntu@<TWCC_HOST>:/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/reads_50M.fa /work/ymj1123ntu/data_50M/
scp ymj1123ntu@<TWCC_HOST>:/work/ymj1123ntu/gfm_embedding_classification/data/balanced_50M/labels_50M.tsv /work/ymj1123ntu/data_50M/
```

或者如果兩邊無法直接 SSH，先從 TWCC 下載到本地，再從本地上傳到 Taiwania-2。

---

## 4. Step 2: 資料準備（切 Train/Val + 分檔）

MetaTransformer 預期的資料格式：
- **目錄模式**：讀取目錄下的所有 `.fa` 檔
- **多 worker**：需要多個 `.fa` 檔（至少等於 `num_workers` 數量）

以下 Python script 會：
1. 讀取 50M FASTA
2. 做 90/10 stratified train/val split（seed=42，stratified by genus，和我們的 GFM classifier 一致）
3. 將 train/val 寫入多個 `.fa` chunk 檔
4. 生成 genus_mapping.tab 和 species_mapping.tab

**請在 Taiwania-2 上建立並執行此 script**：

```python
#!/usr/bin/env python3
"""
prepare_metatransformer_data.py
Split our 50M balanced FASTA into MetaTransformer-compatible train/val directories.
"""

import os
import sys
import numpy as np
from collections import defaultdict

# ============================================================
# Configuration
# ============================================================
FASTA_PATH = "/work/ymj1123ntu/data_50M/reads_50M.fa"
LABELS_PATH = "/work/ymj1123ntu/data_50M/labels_50M.tsv"
OUTPUT_BASE = "/work/ymj1123ntu/data_50M/metatransformer_format"

VAL_RATIO = 0.1
SEED = 42
NUM_TRAIN_CHUNKS = 16   # split train into 16 files for multi-worker loading
NUM_VAL_CHUNKS = 4      # split val into 4 files

# ============================================================
# 1. Read labels TSV to get genus labels for stratified split
# ============================================================
print("Reading labels TSV...")
genus_labels = []
species_labels = []
seq_ids = []
with open(LABELS_PATH, "r") as f:
    header = f.readline()  # skip header
    for line in f:
        parts = line.strip().split("\t")
        # idx, seq_id, species_class, genus_class, genus_name, species_name
        seq_ids.append(parts[1])
        species_labels.append(int(parts[2]))
        genus_labels.append(int(parts[3]))

n_total = len(genus_labels)
genus_labels = np.array(genus_labels)
species_labels = np.array(species_labels)
print(f"  Total reads: {n_total:,}")
print(f"  Unique genera: {len(np.unique(genus_labels))}")
print(f"  Unique species: {len(np.unique(species_labels))}")

# ============================================================
# 2. Stratified train/val split (matching GFM classifier)
# ============================================================
from sklearn.model_selection import train_test_split

indices = np.arange(n_total)
train_idx, val_idx = train_test_split(
    indices,
    test_size=VAL_RATIO,
    stratify=genus_labels,
    random_state=SEED,
)
train_set = set(train_idx.tolist())
val_set = set(val_idx.tolist())
print(f"  Train: {len(train_idx):,}, Val: {len(val_idx):,}")

# ============================================================
# 3. Create output directories
# ============================================================
# genus and species share the same data; only config differs
train_dir = os.path.join(OUTPUT_BASE, "train")
val_dir = os.path.join(OUTPUT_BASE, "val")
os.makedirs(train_dir, exist_ok=True)
os.makedirs(val_dir, exist_ok=True)

# ============================================================
# 4. Read FASTA and write chunked train/val files
# ============================================================
print("Splitting FASTA into train/val chunks...")

# Pre-calculate chunk assignments
train_count = len(train_idx)
val_count = len(val_idx)
reads_per_train_chunk = (train_count + NUM_TRAIN_CHUNKS - 1) // NUM_TRAIN_CHUNKS
reads_per_val_chunk = (val_count + NUM_VAL_CHUNKS - 1) // NUM_VAL_CHUNKS

# Open chunk file handles
train_handles = []
for i in range(NUM_TRAIN_CHUNKS):
    fh = open(os.path.join(train_dir, f"reads_{i:03d}.fa"), "w")
    train_handles.append(fh)

val_handles = []
for i in range(NUM_VAL_CHUNKS):
    fh = open(os.path.join(val_dir, f"reads_{i:03d}.fa"), "w")
    val_handles.append(fh)

train_counter = 0
val_counter = 0
read_idx = 0
current_header = None
current_seq_lines = []

def flush_read(header, seq_lines, idx):
    global train_counter, val_counter
    seq_text = "".join(seq_lines)
    if idx in train_set:
        chunk_id = train_counter % NUM_TRAIN_CHUNKS
        train_handles[chunk_id].write(header + "\n")
        train_handles[chunk_id].write(seq_text + "\n")
        train_counter += 1
    elif idx in val_set:
        chunk_id = val_counter % NUM_VAL_CHUNKS
        val_handles[chunk_id].write(header + "\n")
        val_handles[chunk_id].write(seq_text + "\n")
        val_counter += 1

with open(FASTA_PATH, "r") as f:
    for line in f:
        line = line.strip()
        if line.startswith(">"):
            if current_header is not None:
                flush_read(current_header, current_seq_lines, read_idx)
                read_idx += 1
                if read_idx % 5_000_000 == 0:
                    print(f"  Processed {read_idx:,} / {n_total:,} reads...")
            current_header = line
            current_seq_lines = []
        else:
            current_seq_lines.append(line)
    # last read
    if current_header is not None:
        flush_read(current_header, current_seq_lines, read_idx)
        read_idx += 1

# Close all handles
for fh in train_handles:
    fh.close()
for fh in val_handles:
    fh.close()

print(f"  Train reads written: {train_counter:,} ({NUM_TRAIN_CHUNKS} chunks)")
print(f"  Val reads written: {val_counter:,} ({NUM_VAL_CHUNKS} chunks)")

# ============================================================
# 5. Create mapping files
# ============================================================
print("Creating mapping files...")

mapping_dir = os.path.join(OUTPUT_BASE, "sequence_metadata")
os.makedirs(mapping_dir, exist_ok=True)

# Read genus and species names from TSV
genus_names = {}
species_names = {}
with open(LABELS_PATH, "r") as f:
    header = f.readline()
    for line in f:
        parts = line.strip().split("\t")
        g_class = int(parts[3])
        g_name = parts[4]
        s_class = int(parts[2])
        s_name = parts[5]
        if g_class not in genus_names:
            genus_names[g_class] = g_name
        if s_class not in species_names:
            species_names[s_class] = s_name

# Write genus mapping
with open(os.path.join(mapping_dir, "genus_mapping.tab"), "w") as f:
    f.write("Class\tGenus\n")
    for cls_id in sorted(genus_names.keys()):
        f.write(f"{cls_id}\t{genus_names[cls_id]}\n")

# Write species mapping
with open(os.path.join(mapping_dir, "species_mapping.tab"), "w") as f:
    f.write("Class\tSpecies\n")
    for cls_id in sorted(species_names.keys()):
        f.write(f"{cls_id}\t{species_names[cls_id]}\n")

print(f"  Genus mapping: {len(genus_names)} classes")
print(f"  Species mapping: {len(species_names)} classes")
print("\nDone! Output directory structure:")
print(f"  {OUTPUT_BASE}/")
print(f"    train/          ({NUM_TRAIN_CHUNKS} .fa files)")
print(f"    val/            ({NUM_VAL_CHUNKS} .fa files)")
print(f"    sequence_metadata/")
print(f"      genus_mapping.tab")
print(f"      species_mapping.tab")
```

**執行方式**：

```bash
cd /work/ymj1123ntu
pip install scikit-learn  # 如果還沒裝的話
python3 prepare_metatransformer_data.py
```

---

## 5. Step 3: MetaTransformer Config 設定

MetaTransformer 的 code 位於 `/home/ymj1123ntu/MetaTransformer/`（或你已有的路徑）。
GitHub 來源：https://github.com/alexwichma/MetaTransformer

需要修改或建立以下 config 檔（位於 `src/config/` 下）。

### 5.1 Dataset config

**建立 `src/config/dataset/genus_50M.yaml`**：
```yaml
train_set_path: "/work/ymj1123ntu/data_50M/metatransformer_format/train"
validation_set_path: "/work/ymj1123ntu/data_50M/metatransformer_format/val"
```

**建立 `src/config/dataset/species_50M.yaml`**：
```yaml
train_set_path: "/work/ymj1123ntu/data_50M/metatransformer_format/train"
validation_set_path: "/work/ymj1123ntu/data_50M/metatransformer_format/val"
```

### 5.2 主 config

複製 `src/config/config.yaml` 為兩個版本：

**`src/config/config_genus_50M.yaml`** — Genus 訓練用：
```yaml
cfgs:
  dataset: genus_50M
  model: classification_transformer
  optimizer: adam

paths:
  data_path_root: /work/ymj1123ntu/data_50M/metatransformer_format
  vocabulary_path: <你現有的 vocab_12mer.txt 路徑>
  # 如果沒有 vocab 檔案，從 Zenodo 下載：https://doi.org/10.5281/zenodo.7594864

common:
  experiment_name: ???
  prepend_cls_token: False
  resume_model: False

mdl_common:
  input_module: vocab
  kmer_size: 12
  num_classes: 381          # ← 我們的資料有 381 genera
  class_indices: 3          # ← FASTA header 的第 3 個位置是 genus_class
  classification_threshold: 0.5
  sparse_embedding: True

device_settings:
  use_cpu: False
  gpu_count: 1
  gpu_ids: 0
  split_gpus: False

dataloader:
  batch_size: 2048
  num_workers: 13

training:
  save_interval: 1
  logging_interval: 100
  evaluation_interval: 10000
  max_steps: 300000
  early_stop_threshold: 5
  save_top_n_models: 2
  use_cudnn_benchmark: True
  monitor_metric: min loss/val
  amp: True
  lr_scheduler_enabled: False
  warmup_lr_scheduler_enabled: False

dataset:
  train_set_path: "/work/ymj1123ntu/data_50M/metatransformer_format/train"
  validation_set_path: "/work/ymj1123ntu/data_50M/metatransformer_format/val"

optimizer:
  _target_: torch.optim.Adam
  lr: 0.001
```

**`src/config/config_species_50M.yaml`** — Species 訓練用：
```yaml
# 與 genus 版本相同，只改以下兩個欄位：
mdl_common:
  num_classes: 2505         # ← 2,505 species
  class_indices: 1          # ← FASTA header 的第 1 個位置是 species_class
  # 其餘同上
```

### 5.3 重要 config 參數說明

| 參數 | Genus | Species | 說明 |
|------|-------|---------|------|
| `num_classes` | 381 | 2505 | 類別數 |
| `class_indices` | 3 | 1 | FASTA header split by "\|" 後的 label 位置 |
| `input_module` | vocab | vocab | 使用 k-mer 詞彙表嵌入 |
| `kmer_size` | 12 | 12 | 與論文一致 |
| `batch_size` | 2048 | 2048 | 與論文一致 |
| `max_steps` | 300000 | 300000 | 與論文一致 |

### 5.4 Vocabulary 檔案

MetaTransformer 需要 k-mer vocabulary 嵌入表。應該已經在之前跑 MetaTransformer 時下載過了。
如果沒有，從 Zenodo 下載：https://doi.org/10.5281/zenodo.7594864

把路徑填入 config 的 `vocabulary_path`。

---

## 6. Step 4: 訓練

### 6.1 Genus 模型訓練

```bash
cd /home/ymj1123ntu/MetaTransformer/src

# 如果有 conda env
conda activate MetaTransformer

python3 train.py \
    experiment_name=genus_50M \
    experiment_base_dir=/work/ymj1123ntu/MetaTransformer_experiments \
    cfg_path=config/config_genus_50M.yaml \
    data_path_root=/work/ymj1123ntu/data_50M/metatransformer_format
```

### 6.2 Species 模型訓練

```bash
python3 train.py \
    experiment_name=species_50M \
    experiment_base_dir=/work/ymj1123ntu/MetaTransformer_experiments \
    cfg_path=config/config_species_50M.yaml \
    data_path_root=/work/ymj1123ntu/data_50M/metatransformer_format
```

### 6.3 SLURM Script（如果需要用 SLURM 提交）

```bash
#!/bin/bash
#SBATCH -A <你的帳號>           # 替換
#SBATCH -J mt_genus_50M
#SBATCH -p gp1d               # 或其他 partition
#SBATCH --gres=gpu:1
#SBATCH -c 14
#SBATCH -t 24:00:00
#SBATCH -o mt_genus_50M_%j.out
#SBATCH -e mt_genus_50M_%j.err

module load cuda/11.1           # 依 Taiwania-2 環境調整
source activate MetaTransformer # 或你的 conda env

cd /home/ymj1123ntu/MetaTransformer/src

python3 -u train.py \
    experiment_name=genus_50M \
    experiment_base_dir=/work/ymj1123ntu/MetaTransformer_experiments \
    cfg_path=config/config_genus_50M.yaml \
    data_path_root=/work/ymj1123ntu/data_50M/metatransformer_format
```

---

## 7. Step 5: 結果提取

訓練完成後，從以下位置取得結果：

```
/work/ymj1123ntu/MetaTransformer_experiments/genus_50M_<timestamp>/
├── config.yaml         # 實際使用的 config
├── train.log           # 訓練日誌（含 loss、precision、recall）
├── tensorboard/        # TensorBoard logs
└── checkpoints/        # 模型 checkpoints
```

**我需要的結果**：
1. **train.log 的最後 50 行**（含最佳 validation metrics）
2. **最佳 validation precision 和 recall**
3. **訓練總步數和所花時間**
4. **是否有 early stopping**（如果有，在第幾步停的）

---

## 8. 重要注意事項

### 8.1 FASTA header 格式兼容性

我們的 FASTA header 與 MetaTransformer 的 `LabelTransform` 完全兼容：
```
>lbl|{species_class}|{species_name}|{genus_class}|{genus_name}-{read_id}/{pair}
  ^      ^                ^            ^
  |0     |1               |2           |3        ← split("|") 的 index
```

- MetaTransformer 的 `LabelTransform` 會 `int(header.split("|")[class_indices])`
- Genus: `class_indices: 3` → `int("34")` ✓
- Species: `class_indices: 1` → `int("397")` ✓

### 8.2 類別數量差異

我們的資料集有 **381 genera**（vs MetaTransformer 原始的 120 genera），因為我們保留了所有 HGR-UMGS 的 genus 分類。Species 數量相同（2,505）。

### 8.3 Balanced 資料

我們的 50M 資料集是 **balanced** 的（每個 species 約 20,000 reads）。MetaTransformer 原始訓練資料是 unbalanced 的（coverage-based）。這對 MetaTransformer 來說應該是有利的（balanced data 通常更容易學）。

### 8.4 已知的 MetaTransformer 環境

- Code 路徑：`/home/ymj1123ntu/MetaTransformer/`
- Conda env：`MetaTransformer`
- 之前成功跑過原始 HGR-UMGS 資料集
- GPU：V100 32GB

### 8.5 如果遇到 OOM

V100 32GB 應該足夠跑 MetaTransformer（~5M params，batch 2048）。
如果 OOM，可降低 `batch_size` 到 1024 或 512。

### 8.6 不需要修改的 MetaTransformer Code

由於我們的 FASTA header 已經包含正確格式的 integer class IDs，
且 MetaTransformer 的 `class_indices` 參數支持自定義 label 位置，
所以 **不需要修改 MetaTransformer 的任何 Python code**，只需要修改 config。

---

## 9. 預期結果

| Metric | 我們的 GFM (v9/sp_v4) | MetaTransformer on 50M (預期) |
|--------|----------------------|-------------------------------|
| Genus Acc | ~66% | **?** (要看是否 data volume 是瓶頸) |
| Species Acc | ~17% | **?** |

如果 MetaTransformer 在 50M data 上也只有 ~60-70% genus accuracy，
說明 **data volume 是主要瓶頸**，而不是 model architecture。

如果 MetaTransformer 在 50M data 上能達到 ~90%+，
說明 MetaTransformer 的 from-scratch 架構比 NT-v2 + LoRA 更適合這個任務。
