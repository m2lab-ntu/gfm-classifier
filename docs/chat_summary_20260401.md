# Chat Summary — 2026/04/01

> 本文件總結此次對話中的所有工作內容，方便閱讀、交接或回顧。

---

## 1. 完成的工作

### 1.1 MetaTransformer 數據更正（重要）

**問題**：論文、實驗報告、簡報講稿中，MetaTransformer 的數據被錯誤引用。

| 項目 | 錯誤版本 | 更正版本 |
|---|---|---|
| 訓練資料量 | ~92M balanced reads | ~614M (estimated: 300K steps × 2048 batch) |
| "92M" 實際指的是 | 訓練用的 reads 數量 | 92,143 個 MAGs（基因組），不是 reads |
| Genus accuracy | ~98% | 98.9% Precision, 98.3% Recall (validation) |
| 模型架構 | 4-layer, d=256, 8 heads | Best: 1 block, d_model=64 (for k=13) |

**更正的檔案（共 10 個）**：
- `gfm_embedding_classification/README.md`
- `token_level_gfm_classifier/results/experiment_report_20260309.md`（主本 + 副本）
- `thesis/contents/chapter02.tex`（架構描述 + 資料量）
- `thesis/contents/chapter04.tex`（6 處：表格、比較段落、scaling 數字）
- `thesis/contents/chapter05.tex`
- `thesis/front/abstract.tex`
- `docs/0324/speaker_notes.md`
- `docs/0331/speaker_notes.md`
- `docs/microbiome_presentation_script.md`

### 1.2 RC TTA 理論基礎與文獻補充

**RC TTA (Reverse-Complement Test-Time Augmentation) 的發想邏輯：**

1. **生物學基礎**：DNA 是雙股分子，兩條鏈互補反向。定序時，read 等機率來自任一股。因此 read `s` 和其反向互補 `rc(s)` 編碼**完全相同的生物資訊**（相同基因座、相同物種）。

2. **問題**：標準神經網路不滿足股對稱性（`f(s) ≠ f(rc(s))`），即使做了 RC data augmentation 也無法保證一致性。

3. **RC TTA 解法**：推論時分別對 `s` 和 `rc(s)` 做預測，將 logits 平均後取 argmax：
   ```
   ŷ = argmax_k [f(s) + f(rc(s))]
   ```

4. **為何有效**：
   - **變異數降低**：平均兩個相關但帶雜訊的估計值，降低預測變異
   - **對稱性利用**：建構上保證預測不受股方向影響
   - **錯誤抵消**：當模型對不同股產生不同錯誤時，平均傾向於抵消這些錯誤
   - **免費午餐**：不需修改訓練流程，只有推論成本 2x

5. **實驗驗證**：在所有實驗中穩定提升 +1.0~1.5pp accuracy

**新增文獻引用**（加入 `references.bib`）：
- Zhou et al. 2022 — *Towards a Better Understanding of Reverse-Complement Equivariance for Deep Learning Models in Genomics* (PMLR v165)
- Ma 2025 — *Reverse-Complement Consistency for DNA Language Models* (arXiv:2509.18529)
- Brown & Bepler 2021 — *Reverse-Complement Equivariant Networks for DNA Sequences* (bioRxiv)

**論文修改**：
- `chapter02.tex`：重寫 Section 2.7「Data Augmentation for DNA Sequences」，新增 2.7.1「RC Symmetry in DNA」和 2.7.2「Strategies for Exploiting RC Symmetry」，包含完整生物學推導、strand symmetry 公式、三種策略的比較
- `chapter04.tex`：擴充 Section「RC TTA Analysis」，加入理論分析（variance reduction、diminishing returns with RC consistency training、scale independence）

---

## 2. 目前訓練進度

### 2.1 正在執行的 Jobs

| Job | SLURM ID | Epoch | Val Acc | Val F1 | Config epochs | Status |
|---|---|---|---|---|---|---|
| v9 (Genus 50M) | 151659 | 16/30 | 64.45% | 62.65% | 30 | Running, ~6h to timeout |
| sp_v4 (Species 50M) | 151678 | 12/30 | 15.51% | 13.65% | 30 | Running, ~6h to timeout |

### 2.2 飽和分析

**v9 (Genus)**：
- Epoch 12→16 val accuracy: 63.94% → 64.20% → 64.34% → 64.42% → 64.45%
- 每 epoch 改善：+0.26 → +0.14 → +0.08 → +0.03 pp（明顯趨緩）
- 預估再 3-5 epochs 可能觸發 early stopping (patience=5)

**sp_v4 (Species)**：
- Epoch 8→12 val accuracy: 15.17% → 15.24% → 15.39% → 15.44% → 15.51%
- 改善穩定（~0.07 pp/epoch），離飽和還有距離

### 2.3 訓練計劃（與老師討論後確認）

```
50M 跑到飽和 → Hierarchical Classification 測試
```

- 兩個 job 都設定 `num_epochs: 30` + `early_stopping_patience: 5`
- 48hr SLURM timeout 後用 resume 腳本繼續：
  - `slurm/run_genus_v9_extend.sh`
  - `slurm/run_species_v4_50M_resume.sh`
- 訓練完成後自動執行 forward-only eval + RC TTA eval

---

## 3. 已完成的實驗總覽

| Version | Task | Data | Val Acc | RC TTA | F1-macro | 狀態 |
|---|---|---|---|---|---|---|
| v3 | Genus | 500K imbal. | 53.92% | 55.36% | 25.82% | Done |
| v4 | Genus | 500K imbal. | 53.75% | 55.29% | 25.70% | Done |
| v5b | Genus | 500K, LA τ=0.3 | 52.29% | 53.58% | 26.53% | Done |
| v6 | Genus | 500K, RC consist+LA | — | 50.79% | — | Done |
| v7 | Genus | 500K, RC consist | 54.10% | 55.18% | — | Done |
| v8 | Genus | 5M balanced | 62.02% | 63.05% | 37.97% | Done |
| **v9** | **Genus** | **50M balanced** | **64.45%** | **TBD** | **62.65%** | **Training (ep16/30)** |
| v11 | Genus (shallow) | 50M balanced | ~36% | — | — | Done |
| sp_v1 | Species | 500K | — | 8.32% | — | Done |
| sp_v2 | Species | 500K, LA | — | 8.37% | 20.0% | Done |
| sp_v3 | Species | 500K, sampler | — | 8.01% | 19.9% | Done |
| **sp_v4** | **Species** | **50M balanced** | **15.51%** | **TBD** | **13.65%** | **Training (ep12/30)** |

---

## 4. 關鍵結論

1. **Data volume 遠比 model tricks 重要**：500K→5M 提升 +7.76pp，所有 training tricks 最多 ±0.5pp
2. **RC TTA 普遍有效**：+1.0~1.5pp，不受 data scale 影響
3. **Class balance 關鍵**：balanced sampling 讓 F1=0 classes 從 9 降到 2
4. **v11 shallow ablation**：證明 pre-trained 29-layer backbone 比 1-layer from scratch 好（64% vs 36%）
5. **MetaTransformer 的差距主要來自資料量**（~614M vs 50M），而非模型架構

---

## 5. 檔案結構

```
/work/ymj1123ntu/
├── token_level_gfm_classifier/     # 主專案（⚠️ 無 git）
│   ├── configs/                     # 訓練配置 YAML
│   ├── scripts/                     # train.py, evaluate.py, dataset.py
│   ├── slurm/                       # SLURM 提交腳本
│   ├── results/                     # 模型 checkpoints + 訓練歷史
│   └── docs/                        # 簡報圖片、講稿、本總結
├── thesis/                          # 碩士論文 LaTeX（有 git，大量未 commit）
├── gfm_embedding_classification/    # Phase 1 舊專案（有 git + GitHub remote）
└── Wichmann-2023-*.pdf              # MetaTransformer 論文
```

---

## 6. Git 備份狀態（⚠️ 需要處理）

| Repo | Git | Remote | 狀態 |
|---|---|---|---|
| `token_level_gfm_classifier/` | **無** | **無** | ⚠️ 完全沒有版本控制 |
| `thesis/` | 有 | `NTU-Thesis-Writing-Template` (template) | ⚠️ 大量修改未 commit，remote 是模板 |
| `gfm_embedding_classification/` | 有 | `m2lab-ntu/gfm_embedding_classification` | 有少量未 commit 的 MetaTransformer 修正 |

---

## 7. 後續待辦

- [ ] 等 v9/sp_v4 timeout 後重新 sbatch resume 腳本
- [ ] v9/sp_v4 跑到飽和後，取得 RC TTA 最終數字
- [ ] 實作 Hierarchical Classification（先用 50M 驗證可行性）
- [ ] 建立 `token_level_gfm_classifier` 的 git repo 並 push 到 GitHub
- [ ] thesis 建立獨立 remote 並 commit/push
- [ ] 更新 chapter04 的 v9/sp_v4 最終結果（等訓練完成）
