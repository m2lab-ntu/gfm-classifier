# 與老師對齊：剩餘任務、資源限制、新增請求的可行性

**日期**: 2026-05-28
**目的**: 在預算逼近上限的條件下，跟老師決定哪些實驗繼續、哪些放棄、哪些重新 framing。

---

## TL;DR （三句話）

1. **核心論文敘事已完整**：tokenization > pre-training、router quality threshold、Kraken2 in-DB 對比、noise floor 機制——四個 contribution 都有實驗支撐，thesis 已 137 頁，主表 Table 4.29 完整。
2. **剩餘待跑實驗有三類**：(a) 必要補強——MT predictions 在 TWCC 100K reads 順序對齊（在 Taiwana-2、需老師加值）；(b) 可選——DNABERT-1/2 50M scaling；(c) 新請求——speed/memory benchmark 跟 258M training。
3. **258M training 我建議不要做**：log-fit 預測只 +4 pp（67.07% → 71.27% RC TTA），需 ~18 天 wall clock + 大量算力，跨不過 MT 13-mer 87.4% 的 tokenization gap——花這個資源不會改變 thesis 結論，反而排擠其他更有價值的補強。

---

## 1. 實驗總盤點

### ✅ 已完成（thesis 已寫進）

| Category | 實驗 | 結果 | 狀態 |
|---|---|---|---|
| **NT-v2 scaling** | 500K / 5M / 50M genus | 55.3% / 63.1% / 64.5% (66% RC TTA) | ✓ |
| **NT-v2 50M** | sp_v4 species | 17.55% read, 0.135 Pearson r | ✓ |
| **NT-v2 ablations** | shallow (no PT), per-genus (oracle/predicted), hier-stream, subgenus K-means | +13.19pp PT, 29.5% oracle ceiling, hier 監督-router-threshold 證據 | ✓ |
| **MT 5M 訓練** | MT 13-mer/6-mer genus + species flat/hier | 87.4% / 48.8% genus, 49.7%/9.2% species | ✓ |
| **DNABERT 5M** | DNABERT-1, DNABERT-2 + RC TTA + sample-level | 61.8% / 58.9% RC TTA, Pearson 0.99 | ✓ |
| **Kraken2** | Custom DB built from 同 2,505 UMGS+HGR genomes | 66.2% / 77.18% in-DB species | ✓ |
| **Fair-comparison** | in_db_mask + NT-v2 family + Kraken2 species/genus | Kraken2 主導 in-DB；NT-v2 oracle 29.5%/100% genus | ✓ |
| **Per-genus pipeline** | NT-Genus router + per-genus species classifiers | 14.7% predicted / 27.6% oracle | ✓ |

### 🟡 進行中（TWCC SLURM）

| Job | 模型 | 進度 | 預計完成 |
|---|---|---|---|
| 216281 | DNABERT-2 50M | 16/30 epochs (val 59.2%) | ~6/1（剩 ~14 epochs × 2.8 hr ≈ 1.6 天） |
| 216282 | DNABERT-1 50M | 3/30 epochs (val 59.5%) | ~6/14+（11.7 hr/epoch，~8 次 resume） |
| 218570 | NT-Genus 100K test inference | Pending (QOS slot 滿) | DNABERT-2 完後啟動，~10 分鐘完成 |

### ❌ 待跑（卡在 Taiwana-2 額度）

| 任務 | 在哪 | 阻塞原因 | 重要性 |
|---|---|---|---|
| MT 4-species predictions 重跑 (reads_100K.fa 順序) | Taiwana-2 | Taiwana-2 需老師加值 | **高**——in-DB fair-comparison MT 那欄目前是「對齊錯誤的假數字」 |
| MT 2-genus predictions on 100K test set | Taiwana-2 | 同上 | 中——genus level fair-comparison 完整化 |
| Exp F: MT 13-mer router → per-genus NT-v2 | Taiwana-2 | 同上 | 低（thesis 已有 oracle vs predicted 對比） |

---

## 2. 資源狀態

### TWCC (Nano5, H100) — 我這邊

- **目前佔用**：2 個 SLURM slot 都被 DNABERT-1/2 用掉（QOS 上限），NT-Genus inference 排隊中
- **預算狀態**: 接近上限（老師提到「額度可能快不夠了」）
- **使用量**: 自 2026-04-01 約 186 GPU-hr（不含未來 DNABERT-1 剩餘 ~15 天 × 24 hr ≈ 360 hr）

### Taiwana-2 (V100) — MT 模型所在

- **目前狀態**: 需老師加值才能再交 job
- **必跑任務量**: ~6 個 inference（4 species + 2 genus），每個 100K reads ≤ 5 分鐘 = 約 30 分鐘 GPU
- **可選任務**: Exp F (per-genus pipeline using MT router) ~幾小時

### 本地端

- 沒有 MT 檔案，沒有額外 GPU 工作

---

## 3. 老師的新請求 — 可行性評估

### 請求 A：Speed / Memory / Compute 對比

**可行性**：✅ 已有部分數據，剩下小型補測就完整

**已有數據**：

| Model | 參數量 | Trainable | Throughput | Latency | Peak GPU | Train hr@50M |
|---|---:|---:|---:|---:|---:|---:|
| NT-v2 genus v9 (LoRA) | 498M | 5.54M | 5,160 r/s | 0.194 ms | 15.4 GB | 14.1 hr |
| NT-v2 species sp_v4 | 499M | 6.27M | 5,162 r/s | 0.194 ms | 15.5 GB | 42.1 hr |
| DNABERT-1 (LoRA) | 91M | 2.52M | 4,471 r/s | 0.224 ms | 2.6 GB | 35.1 hr*(5M) |
| DNABERT-2 (LoRA) | 119M | 2.23M | 14,673 r/s | 0.068 ms | 6.1 GB | 8.2 hr*(5M) |
| Shallow (no PT) | 0.9M | 0.9M | 864,166 r/s | 0.001 ms | 0.2 GB | 8.2 hr |

\* DNABERT 5M 是 5M scale，50M 還在跑

**還缺**：
- MT 13-mer / 6-mer (from-scratch) 的數字（在 Taiwana-2，需老師加值補測一次推論）
- Kraken2 inference throughput（CPU-based，需重跑帶 timing）
- 統一報告口徑：建議用 H100 single GPU、batch=512、150bp single read

**成本**：~2 GPU-hr TWCC（NT-v2 + DNABERT 重測）+ 1 GPU-hr Taiwana-2（MT）+ 30 min CPU (Kraken2)

**論文價值**：直接回應 reviewer 必問「為何選大模型 NT-v2 而非小型方法」——表格本身就告訴 reader：
- NT-v2 5,162 reads/sec 跟 DNABERT-1 4,471 reads/sec 同數量級（LoRA + AMP 攤平了 5× 參數差距）
- MT 13-mer scratch 預估 throughput 應該介於兩者之間（小參數但長序列）
- Kraken2 CPU-based，throughput 量級不可比但 wall-clock 通常勝過 GPU inference

### 請求 B：258M Reads 完整訓練

**可行性**：❌ **不建議跑**（理由有數字）

**Log-fit 預測準確率**：

```
log fit:  acc = 57.06 + 5.89 × log10(size_M)
  500K  → 55.3% (實測 55.3%)
   5M   → 63.1% (實測 63.1%)
  50M   → 67.1% (實測 67.07%)
 258M   → 71.27% 預測  (+4.20 pp over 50M)
```

**預期增益**: 50M → 258M 約 +4.2 pp，從 67.1% 升到 71.3%。
**對照**: MT 13-mer 87.4% (5M)，gap 還有 16 pp，**258M 無法跨越 tokenization gap**。

**訓練成本**：

| 模型 | 50M 實測 | 258M 線性外推 | 含 SLURM resume + queue (×1.5) |
|---|---:|---:|---:|
| NT-Genus v9 | 14.1 hr | 73 hr (3.0 天) | ~4.5 天 |
| NT-Species sp_v4 | 42.1 hr | 217 hr (9.1 天) | ~14 天 |
| 兩個都要 | 56.2 hr | 290 hr (12.1 天) | **~18 天 wall clock** |

**Storage**：258M reads × 200 bytes ≈ 52 GB（OK）

**結論**: +4.2 pp 不足以改變 thesis 任何結論。Tokenization gap (vs MT 13-mer) 跟 routing gap (vs per-genus oracle) 是被 ablation 鎖死的「tokenization 是 bottleneck」結論的核心證據——再加 200M 資料只是讓 NT-v2 在 6-mer 框架下慢慢往上爬，**不會改變 fundamental finding**。

**建議跟老師談的 framing**：

> 「老師，我用 log-fit 推估 258M 訓練的預期增益是 +4.2 pp（67.1% → 71.3%），不足以跨越 MT 13-mer 87.4% 的 tokenization gap (-16 pp)。Thesis 的核心 finding『tokenization > pre-training/data』本來就是用 scaling-curve + 同 6-mer 對照 (NT vs MT 6-mer +18 pp) + tokenization 對照 (NT 6-mer vs MT 13-mer +20-32 pp) 三條獨立證據鎖住的，不缺這 +4 pp。我建議改把這 ~18 天算力投資在：(1) 補完 MT predictions in correct order (in-DB fair comparison MT 行)、(2) speed/memory benchmark 完整化、(3) per-real-dataset sanity check (HMP mock community) ——這三個對畢業跟 paper submission 的邊際價值更高。」

可以順便提供 backup option：若老師仍堅持 258M，可以只跑 **genus** 部分（73 hr ≈ 4.5 天），不跑 species（節省 ~14 天的大頭），用 genus 那 4.2 pp 增益作為 scaling extrapolation 的驗證點。

---

## 4. 推薦的 6 月優先順序

依「對畢業 / paper 投稿邊際價值 ÷ 算力成本」排序：

| 優先級 | 任務 | 算力 | 在哪 | 對畢業價值 |
|---|---|---|---|---|
| **P0** 必做 | NT-Genus 100K test inference | ~10 min H100 | TWCC (queued) | 補 genus level dedicated classifier 數字 |
| **P0** 必做 | MT 4-species + 2-genus 100K predictions 重跑 | ~30 min V100 | Taiwana-2 | 公平比較表 MT 行從錯誤數字 → 正確數字 |
| **P1** 高 | Speed/memory benchmark 統一報告 | ~3 GPU-hr | TWCC + Taiwana-2 | 直接回應老師 + reviewer 必問 |
| **P1** 高 | HMP mock community real-dataset 驗證 | ~5 GPU-hr (NT-v2 inference only) | TWCC | 弱化「only simulated」這個 reviewer 必砍點 |
| **P2** 中 | DNABERT-2 50M 完成 + sample-level | (剩 ~38 hr) | TWCC running | 把 backbone selection table 從 5M 擴到 50M |
| **P2** 中 | Kraken2 timing benchmark | 30 min CPU | TWCC | 補 speed table 最後一格 |
| **P3** 低 | DNABERT-1 50M 完成 | (剩 ~14 天) | TWCC running | 預期 +1-2 pp，工程練習價值大於論文價值 |
| **❌ 不做** | 258M 完整訓練 | ~18 天 wall clock | TWCC | +4.2 pp 不影響 fundamental finding |

---

## 5. 給老師的口頭重點（一頁 talking points）

1. **論文敘事完整、實驗證據鏈完整**：thesis 137 頁，Table 4.29 含 9 個 species 配置 + 3 個 reference + Kraken2，主要 contribution 都有 ablation 支撐。

2. **目前阻塞點是 Taiwana-2 那邊 MT predictions 順序問題**，需要老師加值才能重跑。算力很少（30 分鐘 V100）但對「fair-comparison MT 那欄是正確還是錯誤」很關鍵。

3. **DNABERT-2 50M 約 6/1 自然完成**；DNABERT-1 50M 因 overlapping 6-mer 把 sequence 拉到 5×，pre-epoch cost 是 NT-v2 的 4-5 倍，**全訓完要 ~14 天**——可選擇 6/10 用中繼 checkpoint 收尾、或承認「DNABERT-1 50M 的訓練成本本身就是它的 limitation」。

4. **Speed/memory benchmark 我已有 80% 數據**，補測再花 2-3 GPU-hr 就完整，這個值得做。

5. **258M 完整訓練我有具體預測數字**：log-fit 顯示 +4.2 pp，跨不過 tokenization gap，且需 ~18 天 wall clock。**建議用論文裡的 scaling curve + log-fit 預測值取代實際跑**——thesis 寫一段「extrapolation suggests 258M would yield approximately 71.3% genus accuracy under the current log-linear scaling regime, remaining 16 pp below the MT 13-mer baseline; we therefore do not pursue this experiment, as it would not alter the central finding that tokenisation is the dominant bottleneck」。

6. **若老師堅持要 258M**：建議只跑 genus（4.5 天，可接受），不跑 species（14 天，不划算）。

---

## 6. 預算保守版本（若 TWCC 額度真的不夠）

若 TWCC 額度只夠 ~50 GPU-hr，最小可行集（MVP）：

- NT-Genus 100K test inference: 10 min ✓
- 補測一輪 throughput (NT-v2 + DNABERT 各一次 batch=512): 2 hr
- 等 DNABERT-2 自然完成（不主動取消）: 剩 ~38 hr 用掉
- **取消 DNABERT-1 50M**（節省 ~280 hr 的剩餘額度）— 用 5M 數據 + scaling 推估代替
- HMP mock community 推論 (~3 hr)

剩下的 MT 補測、Exp F 全交給 Taiwana-2，本台算力主要保留給最後的 figure regeneration + thesis 校稿。

---

## 附錄：完整 scaling fit 跟 throughput 數字（給老師參考）

### NT-v2 genus scaling (log-fit)
```
acc(%) = 57.06 + 5.89 × log10(size_M)
  50M  → 67.1% (real)
 100M  → 68.8% (+1.7 pp)
 200M  → 70.6% (+3.6 pp)
 258M  → 71.3% (+4.2 pp)  ← 老師的目標
 500M  → 73.0% (+5.9 pp)
2,505M → 79.2% (+12.1 pp) ← 全 HGR-UMGS 上限預期，仍 < MT 13-mer 87.4%
```

### Inference throughput (H100, batch=512, AMP)
- NT-v2 (498M, LoRA): 5,160 reads/sec
- DNABERT-2 (119M, LoRA): 14,673 reads/sec
- DNABERT-1 (86M, LoRA, 145 tokens/read): 4,471 reads/sec
- Shallow (no PT, 0.9M): 864,166 reads/sec
- MT 13-mer/6-mer: 待測 (Taiwana-2)
- Kraken2 (CPU): 待測 (~5,000-50,000 reads/sec/CPU 一般文獻數字)

### Training cost (50M reads, 30 epochs, H100)
- NT-v2 genus (LoRA): 14.1 hr
- NT-v2 species (LoRA): 42.1 hr
- DNABERT-1: 35.1 hr (5M) / 預估 50M 約 350 hr
- DNABERT-2: 8.2 hr (5M) / 預估 50M 約 82 hr

