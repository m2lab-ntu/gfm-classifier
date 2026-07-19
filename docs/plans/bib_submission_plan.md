# BIB 投稿計畫（Briefings in Bioinformatics）

最後更新：2026-07-03
狀態：策略確定，尚未開始改寫 manuscript
完整分析原文（含互動式表格）：https://claude.ai/code/artifact/9418b645-2190-445f-90e9-2e3378c13364（`論文全圖`章節後方 BIB 投稿分析段落）

---

## 一句話結論

現在的碩士論文「以 thesis 形式」直接投 BIB 不適合（BIB 是偏 review 期刊，不收 pure original research）。
需要重新定位為 **Problem-solving Protocol**（2,000–5,000 字），敘事從「我提出 NT-v2+LoRA 方法」改成「回答一個 methodological 問題：GFM 該如何被評估用於 metagenomic taxonomic classification」。

適合度：中等偏高，但需要大改；且**必須先補 out-of-genome generalization 實驗**，否則 13-mer 98.7% 的 closed-set lookup 質疑無法回應。

---

## 標題（兩個選項）

- **選項 A**（直接強調 finding）：
  *Benchmarking genomic foundation models for metagenomic taxonomic classification reveals tokenization as the dominant bottleneck*
- **選項 B**（問句式，BIB 風格更強）：
  *How should genomic foundation models be evaluated for metagenomic taxonomic classification? A benchmark of pre-training, tokenization, and data scaling*

## 摘要草稿（Background/Methods/Results/Conclusion）

> **Background:** Genomic foundation models (GFMs) have shown promise across genomic tasks, yet their utility for metagenomic short-read taxonomic classification—where reads are 150 bp and taxonomic signal is sparse—remains poorly characterized.
>
> **Methods:** We systematically benchmark NT-v2 (498M, non-overlapping 6-mer), DNABERT, DNABERT-2, and MetaTransformer across 120 genera and 1,535 species, ablating data scale (500K–250M reads), pre-training, tokenization (6/12/13-mer, overlapping vs non-overlapping), and evaluation protocol (read-level accuracy, sample-level abundance estimation, binary detection).
>
> **Results:** Overlapping 13-mer tokenization, not backbone pre-training, determines the performance ceiling: MetaTransformer with overlapping 13-mer (trained from scratch) reaches 87.4% genus Top-1 versus 67.1% for NT-v2 + LoRA under identical data. NT-v2 saturates beyond 50M reads (+0.22 pp for 250M), while the 13-mer model continues scaling (87.5%→98.7%). Pre-training provides +13 pp under fixed 6-mer tokenization. At sample level, NT-v2 achieves Pearson r=0.993 for genus abundance—exceeding Kraken2 (r=0.823) because Kraken2's 30% abstention rate uniformly suppresses predicted abundances.
>
> **Conclusion:** Tokenization design is the critical factor for GFM-based metagenomic classification; future microbial foundation models should be pre-trained with overlapping long k-mer tokenization to combine discriminative power with representational quality.

## 建議文章結構（8 節）

1. Introduction（1–1.5 頁）— why metagenomics challenges GFMs、現有工具缺口
2. Why metagenomic read classification challenges current GFMs — 150bp/tokenization mismatch/class imbalance
3. Benchmark design & evaluation protocol — 資料生成、leakage control、read-level + sample-level 雙評估
4. Data scaling & the NT-v2 saturation effect — 500K→5M→50M→250M
5. Pre-training versus tokenization — +13pp (pretrain, fixed 6-mer) vs +20pp (tokenization, fixed scratch)
6. Read-level accuracy versus sample-level utility — r=0.993 vs Kraken2 r=0.823；species-level practical threshold
7. **Practical recommendations**（BIB 核心要求，非 specialist 讀者最看重）
8. Limitations and future directions — closed-set caveat、real data、overlapping 13-mer microbial FM 方向

主文只放 4–6 張圖；完整表格、hyperparameters、訓練 command 全放 supplementary。

### 主文建議圖表

1. Benchmark design（資料生成、模型、tokenization、evaluation levels）
2. Data scaling within NT-v2（500K→250M，6-mer saturation）
3. Tokenization ablation（6/12/13-mer × stride，genus + species）
4. Pre-training vs tokenization decomposition（共同 baseline 分解）
5. Sample-level utility（Pearson/Bray-Curtis/ROC AUC）
6. Failure modes（species hierarchy routing bottleneck、low-abundance noise floor）

---

## 4 個 Take-home Messages（重新定位 contribution 用）

1. **GFM fine-tuning is feasible but not sufficient** — NT-v2+LoRA 達 67% genus accuracy，遠低於 overlapping 13-mer model。
2. **Data scaling helps only until the tokenizer ceiling** — NT-v2 6-mer 50M→250M 幾乎飽和（+0.22pp read-level；sample-level Δr=0.0001，完全飽和）；13-mer 同樣資料量繼續大幅提升（87.5%→98.7%）。
3. **Pre-training helps under fixed tokenization** — 相同 6-mer，NT-v2 優於 random-init shallow model +13.19pp。
4. **Tokenization dominates pre-training for short-read taxonomy** — overlapping long k-mer 比大模型 pre-training 更決定 ceiling。

---

## 核心強項 vs 最危險的質疑

### 真正的強項（reviewer 會喜歡）
- 因果設計嚴謹：每個 ablation 只改一個變量（data/pre-training/tokenization/RC TTA），architecture 保持一致
- Read-level → sample-level 雙評估框架：NT-v2 在 genus 豐度估計上超越 Kraken2（r=0.992 vs 0.823）是反直覺且獨特的發現
- Saturation 直接否定 log-linear 預測：250M read-level +0.22pp、sample-level Δr=0.0001（完全飽和），而 13-mer 同樣資料 +11pp
- Noise floor 機制有明確數學解釋（absent genus → ~138 spurious reads/sample = 0.28%），可直接支撐 Practical Recommendations

### 最危險的 reviewer 質疑（依風險排序）
1. **「13-mer 98.7% 是不是 closed-set k-mer lookup？」**——最致命，論文自己已承認。**必須主動做 out-of-genome generalization 實驗**把它轉成 transparency 優點，而非讓 reviewer 先發現。
2. **「為什麼不測真實 metagenomics？」**——ART simulation 對 Kraken2 有結構性優勢。建議加 ZymoBIOMICS mock community（真實 Illumina reads + 已知組成 + DB 不完全覆蓋，正好測 OOD）。
3. **「Kraken2+Bracken baseline 不完整」**——Bracken 對 Kraken2 species-level 做豐度修正，sample-level 指標可能更好；不跑會被說沒用最強 baseline。
4. **「只有 150bp，能否 generalize 到其他 read length？」**——至少在 Discussion 說明限制。

---

## 優先順序（P0–P3）

| 優先 | 工作 | 估計工時 | 效益 | 備註 |
|------|------|---------|------|------|
| **P0** | Out-of-genome generalization（同 genus 留部分 genome 不進 training） | 1–2 天 | 消除「13-mer=lookup」最大風險 | 用現有 pipeline，只改 train/test genome split |
| **P0** | 文章改寫（thesis→journal article） | 2–3 週 | 投稿最低門檻 | 壓到 4,000–5,000 字 + 補 Practical recommendations |
| **P1** | ZymoBIOMICS mock community inference | 3–5 天 | 「real data」質疑最快解法 | 本地 4090 純 inference，不需 training |
| **P1** | Kraken2 + Bracken 完整 genus/species sample-level | 1 天 | 補強 baseline 完整性 | Bracken 是 post-processing，成本低 |
| P2 | Calibrated detection threshold / background correction | 2–3 天 | noise floor 分析延伸為 actionable method | 已有 noise floor 計算，延伸即可 |
| P2 | Centrifuge / Kaiju baseline | 1–2 天 | 加寬 classical baseline 範圍 | 時間不足可只報 genus-level |
| P3 | Read length ablation (75/150/250bp) | 1 週 | 加分非必要 | 需重新模擬+訓練 |

---

## Practical Recommendations 表格（必加一節）

| 使用情境 | 建議 |
|---------|------|
| Read-level genus classification | Overlapping long k-mer model 仍優先（87% vs 67%）|
| Sample-level abundance estimation | 67% read accuracy 可能已足夠（r=0.993），但需注意 systematic bias |
| Low-abundance taxa 偵測 | 需更高 read accuracy 或 statistical calibration（noise floor 問題）|
| Species-level classification | NT-v2 6-mer 不足；應使用 long-k tokenizer 或 stronger router |
| GFM 選擇 | 不只看 backbone size，要看 tokenizer 是否保留 taxonomic signal |
| 未來模型設計 | Microbial pretraining + overlapping 12/13-mer tokenizer（GTDB >400K genomes）|

---

## 替代期刊（如不補實驗，或 BIB 被拒）

- **Bioinformatics Advances** — 對 original computational method/benchmark 容忍度高於 BIB
- **BMC Bioinformatics** — 接受 original benchmark/software comparison
- **NAR Genomics & Bioinformatics** — OA；接受 methods/benchmark/tooling
- **GigaScience** — 強調 reproducibility；接受 workflow/data article

---

## 投稿前必備文件 checklist

- [ ] Manuscript：英文 journal article 格式，非 thesis 格式
- [ ] 3–5 Key Points（BIB 特別要求的 bullet summary）
- [ ] Data Availability Statement（endmatter，需 GitHub/Zenodo DOI）
- [ ] Code Availability（reproducible scripts + model config）
- [ ] Cover Letter（說明為何適合 BIB：protocol/benchmarking，非 original research）
- [ ] AI 揭露（cover letter + Methods/Acknowledgements 聲明 AI 協助；AI 不能列作者）
- [ ] Conflict of Interest
- [ ] Funding
- [ ] Author Contributions（CRediT taxonomy 逐一說明）
- [ ] Supplementary Tables（完整 hyperparameters、dataset split、training command）
- [ ] Reviewer suggestions（建議 2–3 位 GFM/metagenomics 領域 reviewer）

---

## 關鍵數字速查（manuscript 撰寫時直接引用，來源見 chapter04.tex / chapter05.tex）

### Read-level
- NT-v2 (50M, 6-mer) genus RC-TTA: **67.07%**
- NT-v2 (250M warm, 6-mer) genus RC-TTA: **67.29%**（+0.22pp vs 50M，saturates）
- MT 13-mer (50M) genus: **87.42%**
- MT 13-mer (250M) genus: **98.7%**
- MT 6-mer s1 genus (scratch): **48.87%**（NT-v2 vs 同 tokenization scratch = +18.2pp）
- Random-init shallow (same 6-mer, 50M): NT-v2 pretraining advantage = **+13.19pp**
- MT 13-mer species: **49.62%**（1,535 classes）
- NT-v2 species flat: **15.9%**（1,535 classes）

### Sample-level（genus, friendly pool, 99,742 reads）
| 模型 | read_acc | Pearson r | Bray-Curtis |
|------|---------|-----------|-------------|
| MT 13-mer 250M | 98.7% | 1.000 | 0.005 |
| MT 13-mer 50M | 87.5% | 0.999 | 0.032 |
| NT-v2 v9 (50M) | 67.1% | 0.993 | 0.098 |
| NT-v2 v15 (250M warm) | 67.3% | 0.993 | 0.098（Δr=0.0001，完全飽和）|
| MT 6-mer s1 | 48.9% | 0.989 | 0.171 |
| NT-v2 genus-balanced | 37.2% | 0.862 | 0.420（反效果）|

### Sample-level genus vs Kraken2（in-DB fair pool, 85,819 reads）
| 模型 | Read Acc | Pearson r | Bray-Curtis | ROC AUC | Sens@95%spec |
|------|---------|-----------|-------------|---------|--------------|
| MT 13-mer genus | 94.9% | 0.9993 | 0.029 | 0.905 | 66.5% |
| NT-v2 v9 genus | 68.9% | **0.992**（>Kraken2）| 0.116 | 0.681 | 17.5%（<<Kraken2）|
| Kraken2 (k=35, in-DB) | 77.7% | 0.823 | 0.126 | **0.966** | **93.5%**（偵測最強）|
| MT 6-mer genus | 51.5% | 0.983 | 0.177 | 0.576 | 9.2% |

### Species-level vs Kraken2（in-DB fair pool）
- Kraken2 species (in-DB): **77.18%** read acc, r=0.847 — dominates every metric
- MT 13-mer flat species: 52.64%, r=0.514
- Kraken2 OOD (219 species outside custom DB): **0%** accuracy；神經模型仍有非零 posterior

### 速度/GPU（H200, 端到端 100K reads, batch 1024）
- NT-v2 genus: 1,221 reads/s, 0.82 ms/read, 6,731 MiB
- MT 13-mer s1 genus: 1,066 reads/s, 0.94 ms/read, 9,355 MiB（tokenization 瓶頸，反而慢於 NT-v2）
- MT 6-mer s6: 3,030 reads/s, 857 MiB（最快最省，但準確率低）
- 訓練峰值記憶體：MT 13-mer 16.5GB vs NT-v2 LoRA 8.8GB

### DDP 基礎設施
- 64 GPU (8節點×8 H200) DDP；冷 NFS 476 min/epoch vs 熱 NFS 43 min/epoch（11×差距）

---

## 給新 chat 的啟動指引

開新 chat 處理投稿時，直接說明：
1. 已讀過本文件（`docs/plans/bib_submission_plan.md`），要開始 P0 任務：out-of-genome generalization 實驗 或 manuscript 改寫
2. Thesis repo 位置：`/work/ymj1123ntu/NTU-Thesis-Writing-Template`（LaTeX 原始碼，已 push 到最新，PDF 靠 GitHub Action 建置——編輯前先 pull，同時只能一個 chat 編輯）
3. 實驗程式碼/結果位置：`/work/ymj1123ntu/gfm-classifier`（scripts/、results_summary/、small_predictions/）
4. Benchmark 結果位置：`/work/ymj1123ntu/benchmark_results`（speed/sample-level/CSV 全在這）
5. 若要看完整互動式分析（含所有表格與卡片），可用 WebFetch 讀 artifact：https://claude.ai/code/artifact/9418b645-2190-445f-90e9-2e3378c13364
