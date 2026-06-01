# 與老師對齊：5/28 → 5/30 進度更新、剩餘任務、新發現

**日期**: 2026-05-30（前一份：2026-05-28）
**目的**: 報告兩天內主要進展、修正之前文件中的論證錯誤、列出仍須老師決定的事項。

---

## TL;DR

1. **MT predictions 順序對齊已完成（5/6）**——in-DB fair-comparison Table 4.30 已寫進 thesis。MT 13-mer hier 因 Taiwana-2 checkpoint 損壞無法產出，但其他五個（13-mer flat、6-mer flat/hier、13-mer/6-mer genus）都到位。
2. **重要新發現：genus level 在 fair-restricted 設定下，MT 13-mer (94.89%) 反超 Kraken2 (77.68%)**——species level Kraken2 仍主導 (77.18% vs 52.64%)，但 genus level 因 Kraken2 30% unclassified rate 在 120-class task 傷害更大，inversion 出現。這補強「learned 跟 k-mer complementary」論點。
3. **OOD framing 已修正**——之前寫「neural retains signal on OOD」是錯的，那 219 GCF species 對 neural 是 in-distribution。正確是 deployment coverage asymmetry（Kraken2 需 reference FASTA, neural 不需要）。Thesis 已更新。
4. **TWCC 雙 DNABERT 50M 都 TIMEOUT**——DNABERT-2 17/30 epochs, DNABERT-1 4/30 epochs。**現在沒有 GPU job 在跑**，需決定要不要 resubmit。

---

## 1. 自 0528 以來的具體進展

### ✅ 完成

| 任務 | 結果 | 影響 |
|---|---|---|
| MT 5 個 predictions 重跑（reads_100K.fa 順序對齊） | 全部驗證 1:1 read order alignment | 解除 in-DB fair-comparison 阻塞 |
| In-DB fair-comparison Table 4.30 寫進 thesis | 8 species + 6 genus models 完整對比 | Section §4.13 多 2 頁 |
| NT-Genus v9 100K test inference | 66.61%（mathematically == NT-Species hier→genus） | 確認 hier pipeline 等價性 |
| Thesis Table 4.29 MT 數字更新 | 從 MT val pool 換成 TWCC 100K test (aligned) | 數字一致性 |
| Discussion 段落修正 OOD framing | 改成 deployment coverage asymmetry | 移除錯誤敘述 |
| Thesis 編譯 | 137 → **139 頁** | — |

### 🔬 重要新發現：Species/Genus level 的「inversion」

| Level | 第一名 | 第二名 | 第三名 |
|---|---|---|---|
| **Species (in-DB)** | Kraken2 77.18% | MT 13-mer 52.64% | NT-v2 oracle 27.69% |
| **Genus (in-DB)** | **MT 13-mer 94.89%** | Kraken2 77.68% | NT-v2 oracle 100% (trivial)* |

\* NT-v2 per-genus oracle 在 genus level 必然 100%（因為 oracle routing 用真實 genus label）。所以 non-trivial 比較中 MT 13-mer 94.89% 是冠軍。

**為什麼會 inversion**：Kraken2 30% reads 沒 commit（unclassified 或 LCA=root）。這個 30% 對 1535-class species task 傷害分散，相對小；但對 120-class genus task 直接損失 30% 預測訊號，傷害集中。MT 13-mer 對所有 reads 都給 prediction，所以在 low-cardinality task 反而完勝。

**論文價值**：
- 強化「complementary」論點：不是「neural 通用、Kraken2 限定」，而是「兩者各有強項，取決於 task granularity」
- Pearson r: Kraken2 species 0.847 / genus 0.823（降），MT 13-mer species 0.514 / genus 0.9993（升）
- 對應 paper discussion 可以寫「Kraken2 的 commit-rate-vs-precision tradeoff 在 high-cardinality task 是優勢、low-cardinality task 是劣勢」

### 🟡 進行中（Taiwana-2）

| 任務 | 進度 | 預計完成 |
|---|---|---|
| Per-genus 13-mer species (Exp F) | 60/81 genera | 未通知 |

完成後可以加上 thesis Table 4.hierarchical-prelim 一行——驗證 router quality threshold 在 MT 13-mer router (87.5%) 端的數據點。

### ⏸️ TWCC 兩個 DNABERT 50M job 都 TIMEOUT

| Job | 結果 | 已訓 | 剩餘預估 |
|---|---|---|---|
| 216281 DNABERT-2 | TIMEOUT @ 48 hr | 17/30 epochs, val 59.22% | ~13 epochs × 2.8 hr ≈ 36 hr（1 個 SLURM job 內可完成）|
| 216282 DNABERT-1 | TIMEOUT @ 48 hr | 4/30 epochs, val 60.07% | ~26 epochs × 11.7 hr ≈ 304 hr ≈ **13 天** |

**現在 TWCC 沒有 GPU job 在跑**。是否 resubmit 是個 decision point（見下方 Section 4 Q2）。

---

## 2. 待跑任務（剩下的）

### 必跑（為 thesis 完整性）

| 任務 | 在哪 | 算力 | 阻塞 |
|---|---|---|---|
| 整合 Per-genus 13-mer (Exp F) 結果 | TWCC（接收 .npz 後 evaluate_sample） | <1 GPU-hr | 等 Taiwana-2 完成 |
| Speed/memory unified benchmark | TWCC H100（需 MT 模型搬遷） | ~3 GPU-hr | 等 Taiwana-2 打包 MT 模型 |
| MT 13-mer hier 重訓 OR 標 N/A | Taiwana-2（重訓）or 接受缺失 | 大or 0 | 老師決定 |

### 可選（投稿補強）

| 任務 | 在哪 | 算力 | 投稿價值 |
|---|---|---|---|
| HMP mock community real-dataset 驗證 | TWCC (NT-v2 inference only) | ~3 GPU-hr | 強——直接弱化「only simulated」reviewer 砍點 |
| 258M 完整訓練 | TWCC | ~290 GPU-hr | **弱**——log-fit 預測 +4.2 pp，跨不過 tokenization gap |

---

## 3. 資源狀況

### TWCC (Nano5, H100)

- 自 4/1 累計使用：**~290 GPU-hr**（含 DNABERT-2 + DNABERT-1 × 48 hr 各兩次）
- 老師反映「額度可能快不夠了」
- 兩個 DNABERT 都 TIMEOUT 沒 resubmit 的話，TWCC 暫時沒有 GPU 消耗

### Taiwana-2 (V100)

- 已加值，目前在跑 Per-genus 13-mer
- MT alignment 已完成 5/6（節省了我們之前擔心的 GPU 需求）

---

## 4. 仍需老師決定的事項

### Q1. DNABERT-2 50M 要不要 resubmit 把 13 epochs 跑完？

- **成本**：~36 hr H100（1 個 SLURM job 內）
- **產出**：完整 50M scaling 數字、加進 backbone selection table（從 5M 拉到 50M）
- **價值**：驗證 NT-v2 50M 跟 DNABERT-2 50M 差距是否如 5M 預期（NT-v2 略勝 DNABERT-2 +5 pp）
- **建議**: **resubmit**——36 hr H100 換 thesis 一個完整的 50M-scale backbone comparison data point，CP 值高

### Q2. DNABERT-1 50M 要不要繼續？

- **成本**：~13 天 wall clock + ~300 GPU-hr（vs 已花的 96 GPU-hr）
- **產出**：DNABERT-1 在 50M 的 RC TTA accuracy（預期 ~62-63%）
- **價值**：DNABERT-1 訓練成本本身就是它的 deployment limitation（11.7 hr/epoch vs NT-v2 2.8 hr/epoch），就算跑完，論點是「DNABERT-1 太慢、實務上不該選」
- **建議**: **取消**——用 5M 數據 + 訓練成本對比論證即可，不需要實際 50M 數字

### Q3. MT 13-mer hier 損壞的 checkpoint 要不要在 Taiwana-2 重訓一次？

- **成本**：MT 13-mer hier 模型訓練時間（不確定，但 hier 通常跟 flat 同量級——Taiwana-2 V100 上應該 1-2 天）
- **產出**：補回 Table 4.29 那一行的數字、補回「3 routers monotonic」的第三個 data point
- **建議**: **不一定**——目前 thesis 已標 N/A 並引用 Section 4.spv4-prelim 的 read-level 三點 monotonic 證據（87.5% router 那點仍然有 read-level 47→51%）。若 Taiwana-2 額度寬裕可以補；若緊張可以接受缺失，論點靠 read-level 證據撐住。

### Q4. 速度/記憶體 benchmark 要做嗎？

- **成本**：~3 GPU-hr H100（搬 MT models + 跑 inference timing）+ 30 分鐘設定環境
- **產出**：統一 H100 throughput / latency / GPU peak memory table，含 NT-v2 / DNABERT-1 / DNABERT-2 / MT 13-mer / MT 6-mer / shallow / Kraken2
- **建議**: **做**——回應老師明確要求，且 ML reviewer 必問。這項一定要做。

### Q5. 258M 完整訓練要不要做？

- **成本**：~290 GPU-hr（NT-v2 genus + species）≈ ~12 天純 GPU + 排隊 ≈ ~18 天 wall clock
- **產出**：log-fit 預測 NT-v2 genus 從 67.07% → 71.27%（+4.2 pp）
- **價值**：跨不過 MT 13-mer 87.4% 的 tokenization gap（-16 pp）；不會改變 thesis 任何 fundamental finding
- **建議**: **不做**——用 thesis 一段 log-fit extrapolation 取代實際訓練。若老師堅持，只跑 **genus 部分**（~4.5 天）作為 scaling extrapolation 的驗證點，species 跳過。

### Q6. HMP mock community real-dataset 驗證要做嗎？

- **成本**：~3 GPU-hr（NT-v2 inference only，HMP 數據集小）+ ~1 天工程（資料準備）
- **產出**：NT-v2 在 1 個 real metagenomic dataset 上的 sample-level 結果
- **價值**：直接弱化「only simulated」這個投稿 reviewer 必砍的點。對 thesis 是 nice-to-have，對 paper submission 是 must-have
- **建議**: **6 月做**——thesis 不必趕著補（先口試完）、submission 前必做。

---

## 5. 6 月優先順序（更新版）

依「對畢業 / 投稿價值 ÷ 算力成本」排序：

| 優先 | 任務 | 算力 | 在哪 | 對畢業/投稿價值 |
|---|---|---|---|---|
| **P0** | DNABERT-2 50M resubmit 完成 | ~36 hr H100 | TWCC | 補完 backbone scaling table |
| **P0** | Speed/memory unified benchmark | ~3 hr H100 + scp | TWCC + Taiwana-2 | 回應老師 + reviewer 必問 |
| **P0** | 接收 Per-genus 13-mer（Exp F）並整合 | <1 hr H100 | TWCC（被動）| 補 router quality threshold 第三點 |
| **P1** | HMP mock community real-dataset 驗證 | ~3 hr H100 | TWCC | submission 前 must-have |
| **P2** | thesis 校稿 + figure regeneration | CPU only | TWCC | 口試前 must |
| **P3** | MT 13-mer hier 重訓 | TBD | Taiwana-2 | Nice-to-have（thesis 已標 N/A） |
| **❌ 跳過** | DNABERT-1 50M 繼續跑 | ~300 hr H100 | TWCC | 13 天不划算，5M 證據已足 |
| **❌ 跳過** | NT-v2 258M 完整訓練 | ~290 hr H100 | TWCC | log-fit extrapolation 取代 |

**總額外算力預算**：~45 GPU-hr H100（含所有 P0 + P1），相當溫和。

---

## 6. 給老師的口頭重點（更新版）

1. **MT 順序對齊已解決**——Table 4.30 補了 in-DB fair-restricted comparison，species/genus 各 8/6 個 models，數字完整可比。

2. **發現一個本來沒預料到的東西**：genus level 在 fair-restricted 下 MT 13-mer (94.89%) 反而超過 Kraken2 (77.68%)。原因是 Kraken2 的 30% unclassified rate 對 120-class task 比 1535-class 傷害更大。這個「inversion」強化 thesis 的 complementary 論點，且 paper 可以多寫一段 commit-rate analysis。

3. **DNABERT-2 50M 還剩 36 hr 沒跑完**（48 hr SLURM cap），是否要 resubmit 把它跑完——CP 值高，建議做。

4. **DNABERT-1 50M 還剩 ~13 天，建議取消**——overlapping 6-mer 把每 epoch 拉到 11.7 hr（NT-v2 4-5×），這個成本本身就是它的 limitation 證據，5M 數據 + 訓練成本對比論證即可。

5. **258M 完整訓練**：log-fit 預測 +4.2 pp，跨不過 tokenization gap，建議用一段 extrapolation paragraph 取代實際跑。

6. **Speed/memory benchmark** 一定要做（你明確要求過），算力很小（3 hr），等 MT 模型從 Taiwana-2 搬過來就立刻做。

7. **OOD framing 修正**：之前 thesis 寫的「neural retains signal on OOD」其實 framing 錯了（那 219 GCF species 對 neural 是 in-distribution），已改成 deployment coverage asymmetry 的正確敘述。這個更新讓 thesis 的論點更嚴謹。

---

## 附錄：thesis Table 4.30 全文（給老師參考用）

### Species level (in-DB 85,819 reads, 1K reads/sample)

| Model | Read Acc | Pearson r | BC | ROC AUC | Sens@95 |
|---|---:|---:|---:|---:|---:|
| NT-Species flat | 17.12% | 0.142 | 0.602 | 0.776 | 52.6% |
| NT-Species hier. | 15.20% | 0.118 | 0.616 | 0.776 | 49.5% |
| NT-v2 per-genus (predicted) | 14.98% | 0.088 | 0.641 | 0.767 | 49.8% |
| NT-v2 per-genus (oracle) | 27.69% | 0.156 | 0.560 | 0.818 | 61.6% |
| MT 6-mer flat | 8.54% | 0.071 | 0.664 | 0.674 | 31.4% |
| MT 6-mer hier. | 6.11% | 0.042 | 0.696 | 0.629 | 23.6% |
| MT 13-mer flat | 52.64% | 0.514 | 0.358 | 0.968 | 89.2% |
| **Kraken2 (in-DB)** | **77.18%** | **0.847** | **0.129** | **0.998** | **99.6%** |

### Genus level (in-DB 85,819 reads, 1K reads/sample)

| Model | Read Acc | Pearson r | BC | ROC AUC | Sens@95 |
|---|---:|---:|---:|---:|---:|
| NT-Genus v9 (≡ NT-Species hier→genus) | 68.88% | 0.992 | 0.116 | 0.681 | 17.5% |
| NT-v2 per-genus router (predicted) | 62.77% | 0.989 | 0.143 | 0.699 | 22.6% |
| NT-v2 per-genus router (oracle) | 100.0% | 1.000 | 0.000 | 0.966 | 93.6% |
| MT 6-mer genus | 51.49% | 0.983 | 0.177 | 0.576 | 9.2% |
| **MT 13-mer genus** | **94.89%** | **0.9993** | **0.029** | 0.905 | 66.5% |
| Kraken2 (genus, in-DB) | 77.68% | 0.823 | 0.126 | 0.966 | 93.5% |

注意：oracle row 是 100% by construction（用真實 genus label routing），不應跟其他 row 直接比較。  
真正的「不平凡 best」是 **MT 13-mer genus 94.89%**。

---

## 附錄：log-fit 對 258M 的預測（給老師 reference）

```
NT-v2 genus RC TTA 實測值：
  500K → 55.29%
   5M  → 63.05%
  50M  → 67.07%

Log-linear fit: acc(%) = 57.06 + 5.89 × log10(size_M)
  100M  → 68.84% (+1.77 over 50M)
  200M  → 70.62% (+3.55)
  258M  → 71.27% (+4.20) ← 老師原本想驗證的目標
  500M  → 72.96% (+5.89)
2,505M → 79.20% (+12.13) ← 全 HGR-UMGS 上限預期，仍低 MT 13-mer 87.4%
```

訓練成本（H100, 50M = 14.1 hr genus / 42.1 hr species, linear scaling）：
- 258M genus: ~73 hr ≈ 3.0 天 純 GPU + queue/resume ≈ ~4.5 天 wall clock
- 258M species: ~217 hr ≈ 9.1 天 純 GPU ≈ ~14 天 wall clock
- 兩個都跑：~290 hr 純 GPU ≈ ~18 天 wall clock + 大量 SLURM resume
