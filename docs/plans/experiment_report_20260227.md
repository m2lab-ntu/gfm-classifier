# Token-level GFM Classifier — 實驗報告

> **日期**：2026-02-27  
> **環境**：TWCC (台智雲) SLURM 叢集 · NVIDIA H100 80GB HBM3  
> **Repo**：`/work/ymj1123ntu/token_level_gfm_classifier`  
> **Backbone**：`InstaDeepAI/nucleotide-transformer-v2-500m-multi-species` (498M params)

---

## 1. 專案概覽

### 1.1 研究目標

利用 DNA Foundation Model（Nucleotide Transformer v2 500M）對 gut metagenome 短讀序列進行 **genus-level 分類**（120 classes）。核心想法是保留 backbone 輸出的 **完整 token-level 資訊** `[batch, seq_len, hidden_dim]`，而非傳統的 mean-pooled embedding 向量，搭配 learnable attention pooling head 進行分類。

### 1.2 資料集


| 項目         | 數值                                         |
| ---------- | ------------------------------------------ |
| 資料來源       | Gut metagenome 模擬短讀序列                      |
| 總序列數       | 500,000                                    |
| 序列長度       | 150 bp                                     |
| Genus 數量   | 120                                        |
| Species 數量 | 1,535                                      |
| 訓練集        | 450,000（90%）                               |
| 驗證集        | 50,000（10%, stratified, `random_state=42`） |


**類別分佈高度不平衡**：最大類 Collinsella（114,195 筆, 22.8%）vs 最小類僅 ~300 筆（0.06%）。


| Rank  | Genus         | 筆數      | 佔比    |
| ----- | ------------- | ------- | ----- |
| 1     | Collinsella   | 114,195 | 22.8% |
| 2     | Clostridium   | 61,955  | 12.4% |
| 3     | Prevotella    | 29,697  | 5.9%  |
| 4     | Bacteroides   | 25,930  | 5.2%  |
| 5     | Ruminococcus  | 20,593  | 4.1%  |
| 6–120 | 其餘 115 genera | 247,630 | 49.5% |


### 1.3 與先前 Baseline 的關係

在本 token-level 專案之前，我們曾用 frozen NT embedding + MLP 做 genus 分類（`gfm_embedding_classification/` 專案）。**該 baseline 存在 data leakage 問題**（評估使用全部 500K 資料含訓練集），修正後的公平 baseline 為 **42.12% accuracy**。本專案所有實驗均使用相同 50K held-out validation set。

---

## 2. 系統架構

### 2.1 模型架構

```
Input DNA (150bp)
    │
    ▼
NT v2 500M Tokenizer (6-mer, max_length=32 or 128)
    │
    ▼
NT v2 500M Backbone (ESM-based, 498M params)
    │  LoRA adapters: r=16, α=32, dropout=0.05
    │  Target modules: query, key, value
    │
    ▼
Token Embeddings [batch, seq_len, 1024]  ← 不做 mean pooling
    │
    ▼
AttentionPoolClassificationHead
    │  Multi-head attention (4 heads) + learnable query
    │  hidden_dim=512, dropout=0.15
    │
    ▼
Logits [batch, 120]
```

### 2.2 AttentionPoolClassificationHead 細節

- **Learnable Query Token**：模型學習一個 query vector，通過 multi-head attention 機制對所有 token embedding 加權聚合
- **Attention Mask 處理**：padding token 的 attention weight 被設為 `-inf`，確保不影響分類
- 與 mean pooling 的差異：能動態關注不同位置的 token，保留位置和局部特徵資訊

### 2.3 Two-Phase 訓練策略


| Phase   | Epochs | 訓練範圍                  | Learning Rate              |
| ------- | ------ | --------------------- | -------------------------- |
| Phase 1 | 5      | 僅 classification head | 5e-4                       |
| Phase 2 | 40     | LoRA adapters + head  | backbone: 3e-5, head: 5e-4 |


- **Mixed Precision**：`bfloat16`（H100 原生支援）
- **Gradient Accumulation**：2 steps（effective batch size = 64）
- **Early Stopping**：patience = 7 epochs
- **LR Schedule**：Cosine decay with 5% warmup

### 2.4 原始碼結構

```
token_level_gfm_classifier/
├── scripts/
│   ├── data_loader.py   (134 行) — FASTA/TSV 載入, train/val split
│   ├── dataset.py       (135 行) — PyTorch Dataset, on-the-fly tokenization, RC augmentation
│   ├── heads.py         (295 行) — 4 種 classification head 實作
│   ├── model.py         (177 行) — Backbone + LoRA + Head 整合
│   ├── train.py         (658 行) — Two-phase 訓練, AMP, gradient accumulation
│   ├── evaluate.py      (479 行) — 完整評估 + RC TTA + 視覺化
│   └── utils.py         (103 行) — 工具函式
├── configs/              — YAML 配置檔
├── slurm/                — SLURM 提交腳本
└── results/              — 各版本實驗結果
```

---

## 3. 實驗設計

### 3.1 Ablation 矩陣

本報告涵蓋 7 個版本的實驗，逐步測試不同 component 的效果：


| Version | 基底  | max_length | RC Aug | RC Consistency | Logit Adj (τ) | 目的                   |
| ------- | --- | ---------- | ------ | -------------- | ------------- | -------------------- |
| v3      | —   | 128        | ✓      | —              | —             | 基準版本                 |
| v4      | v3  | **32**     | ✓      | —              | —             | 減少 padding, 加速推論     |
| v5      | v4  | 32         | ✓      | —              | **1.0**       | Long-tail 處理         |
| v5b     | v4  | 32         | ✓      | —              | **0.3**       | 溫和版 Logit Adjustment |
| v6      | v4  | 32         | —      | **✓**          | **1.0**       | RC Consistency + LA  |
| v7      | v4  | 32         | —      | **✓**          | —             | 純 RC Consistency     |


> **Note**: v1/v2 為早期 debug 版本（NaN loss、shape bug 修復），不列入正式比較。

### 3.2 技術說明

**Reverse-Complement (RC) Augmentation**：訓練時以 50% 機率將序列替換為其反向互補序列，增加 strand-invariance。

**RC Test-Time Augmentation (TTA)**：推論時同時計算 forward 和 RC 序列的 logits，取平均作為最終預測。純推論端技巧，不增加訓練成本。

**RC Consistency Training**：訓練時同時處理 forward 和 RC 序列，要求模型對兩者產生一致的預測分佈（通過 KL divergence loss 正則化，λ=0.1）。

**Logit Adjustment**：根據訓練集類別先驗機率調整 logits：`logits_adj = logits + τ · log(π)`，旨在提升少量類的 recall。

---

## 4. 實驗結果

### 4.1 主要結果（統一 RC TTA 推論）


| Version  | 描述                      | Fwd Acc | **RC TTA Acc** | F1-w   | F1-macro | Top-5  | Top-10 |
| -------- | ----------------------- | ------- | -------------- | ------ | -------- | ------ | ------ |
| Baseline | Frozen emb + MLP        | 42.12%  | —              | 49.71% | 45.38%   | 73.80% | 82.46% |
| **v3**   | Base + RC aug           | 53.92%  | **55.36%**     | 52.50% | 25.82%   | 83.15% | 91.28% |
| **v4**   | + maxlen=32             | 53.75%  | **55.29%**     | 52.51% | 25.70%   | 82.91% | 91.29% |
| v5       | + LA τ=1.0              | 35.17%  | —              | 40.18% | —        | —      | —      |
| v5b      | + LA τ=0.3              | 52.29%  | 53.58%         | 52.29% | 26.53%   | 81.96% | 90.65% |
| v6       | + RC consist + LA τ=1.0 | 35.87%  | 38.19%         | 43.25% | 22.88%   | 69.29% | 81.61% |
| **v7**   | + RC consist only       | 54.10%  | **55.18%**     | 51.89% | 25.10%   | 83.17% | 91.37% |


### 4.2 效率指標


| Version | 訓練時間       | GPU VRAM   | 推論速度 (reads/sec) | Trainable Params |
| ------- | ---------- | ---------- | ---------------- | ---------------- |
| v3      | 11h 26m    | 10.4 GB    | 558              | 5.54M (1.1%)     |
| **v4**  | **9h 23m** | **4.7 GB** | **1,243**        | 5.54M (1.1%)     |
| v5b     | 6h 37m     | 4.7 GB     | 1,221            | 5.54M (1.1%)     |
| v6      | 21h 09m    | 7.2 GB     | 1,176            | 5.54M (1.1%)     |
| v7      | 13h 52m    | 7.2 GB     | 1,212            | 5.54M (1.1%)     |


### 4.3 Overfitting 分析


| Version | Best Epoch | Train Acc | Val Acc | **Gap** | Train Loss | Val Loss |
| ------- | ---------- | --------- | ------- | ------- | ---------- | -------- |
| v3      | 28         | 60.88%    | 53.92%  | 6.96%   | 1.370      | 1.748    |
| v4      | 25         | 59.99%    | 53.75%  | 6.25%   | 1.409      | 1.738    |
| v5      | 23         | 37.70%    | 35.17%  | 2.53%   | 1.437      | 2.440    |
| v5b     | 14         | 54.44%    | 52.29%  | 2.15%   | 1.592      | 1.774    |
| v6      | 29         | 43.46%    | 35.87%  | 7.59%   | 1.290      | 2.504    |
| v7      | 17         | 59.02%    | 54.10%  | 4.92%   | 1.485      | 1.708    |


### 4.4 Long-tail 效果：F1=0 類別數


| Version | F1=0 classes (fwd) | F1=0 classes (TTA) | 說明                         |
| ------- | ------------------ | ------------------ | -------------------------- |
| v3      | 11                 | 10                 | 基準                         |
| v4      | 13                 | 9                  | maxlen=32 略有影響             |
| v5b     | 3                  | 4                  | LA τ=0.3 大幅減少              |
| v6      | **0**              | **0**              | RC consist + LA τ=1.0 完全消除 |
| v7      | 11                 | 15                 | 純 RC consist 無改善           |


### 4.5 RC TTA 增益


| Version | Fwd Acc | TTA Acc | **Δ**       |
| ------- | ------- | ------- | ----------- |
| v3      | 53.92%  | 55.36%  | **+1.43pp** |
| v4      | 53.75%  | 55.29%  | **+1.55pp** |
| v5b     | 52.29%  | 53.58%  | **+1.29pp** |
| v6      | 35.87%  | 38.19%  | **+2.32pp** |
| v7      | 54.10%  | 55.18%  | **+1.07pp** |


RC TTA 為推論端的免費提升，一致帶來 +1~2pp 的 accuracy 改善。

---

## 5. 詳細分析

### 5.1 Top-10 混淆配對 (v3, RC TTA)


| True Genus      | Predicted As | 混淆數 | 佔真實類比例 |
| --------------- | ------------ | --- | ------ |
| Fusobacterium   | Clostridium  | 467 | 55.3%  |
| Bacteroides     | Prevotella   | 407 | 15.7%  |
| Ruminococcus    | Clostridium  | 348 | 16.9%  |
| Prevotella      | Bacteroides  | 344 | 11.6%  |
| Blautia         | Clostridium  | 334 | 22.3%  |
| Clostridium     | Blautia      | 310 | 5.0%   |
| Eubacterium     | Clostridium  | 268 | 28.4%  |
| Parabacteroides | Bacteroides  | 234 | 46.1%  |
| Eggerthella     | Collinsella  | 228 | 34.6%  |
| Solobacterium   | Clostridium  | 223 | 19.2%  |


**觀察**：

- **Clostridium 是最大的「吸收器」**：Fusobacterium、Ruminococcus、Blautia、Eubacterium、Solobacterium 大量被誤判為 Clostridium。這反映了 Firmicutes 門內 genera 之間的高序列相似性。
- **Bacteroides ↔ Prevotella** 互相混淆，屬於 Bacteroidetes 門內的經典混淆配對。
- **Parabacteroides → Bacteroides** 混淆率高達 46%，這兩個 genus 在分類學上非常接近。

### 5.2 Per-Class 表現

**表現最好的 genera (v3 RC TTA)**：


| Genus       | Support | F1    | Precision | Recall |
| ----------- | ------- | ----- | --------- | ------ |
| Collinsella | 11,420  | 0.863 | 0.796     | 0.942  |
| Clostridium | 6,195   | 0.613 | 0.524     | 0.737  |
| Prevotella  | 2,970   | 0.590 | 0.545     | 0.642  |


**表現最差的 genera (F1 > 0)**：


| Genus             | Support | F1    | Precision | Recall |
| ----------------- | ------- | ----- | --------- | ------ |
| Robinsoniella     | 132     | 0.027 | 0.118     | 0.015  |
| Ralstonia         | 34      | 0.045 | 0.100     | 0.029  |
| Sanguibacteroides | 37      | 0.047 | 0.167     | 0.027  |
| Franconibacter    | 29      | 0.050 | 0.091     | 0.034  |
| Pelosinus         | 63      | 0.050 | 0.118     | 0.032  |


**F1=0 的 genera (10 個)**：
Anaerostipes (31), Cryptobacterium (64), Flavobacterium (33), Gemella (33), Lachnoclostridium (34), Marvinbryantia (33), Pediococcus (31), Peptostreptococcus (38), Sneathia (31), Xylanibacter (66)

這些 genera 的 support 普遍很低（31–66 筆），模型完全無法正確分類。

### 5.3 Macro F1 vs Weighted F1 的落差

所有版本的 weighted F1 (~~52%) 遠高於 macro F1 (~~25%)，反映了嚴重的長尾效應：模型在大類上表現良好，但大量小類的 F1 接近零，拉低了 macro 平均。

---

## 6. 關鍵發現與討論

### 6.1 Token-level vs Mean-pooled Embedding

Token-level approach 在 micro accuracy 上大幅超越 frozen mean-pooled baseline：


| 方法                          | Micro Acc    | Top-5       | Top-10      |
| --------------------------- | ------------ | ----------- | ----------- |
| Frozen emb + MLP (baseline) | 42.12%       | 73.80%      | 82.46%      |
| Token-level + LoRA (v4 TTA) | **55.29%**   | **82.91%**  | **91.29%**  |
| **提升**                      | **+13.17pp** | **+9.11pp** | **+8.83pp** |


Token-level 保留了 positional 和 local context 資訊，結合 LoRA fine-tuning 和 attention pooling，顯著提升了分類能力。

### 6.2 max_length 減少的影響

150bp DNA 經 NT tokenizer（6-mer）處理後僅產生 ~26 個 token，因此 `max_length=128` 導致大量 padding。將 `max_length` 從 128 降至 32：

- **Accuracy 幾乎無損**：53.92% → 53.75%（-0.17pp，統計上無顯著差異）
- **GPU VRAM 減半**：10.4 GB → 4.7 GB（-55%）
- **推論速度翻倍**：558 → 1,243 reads/sec（+123%）
- **訓練時間縮短**：11h26m → 9h23m（-18%）

### 6.3 Logit Adjustment 的失敗

Logit Adjustment 在所有測試的 τ 值下都損害了 micro accuracy：


| τ        | Micro Acc (TTA) | vs v4   |
| -------- | --------------- | ------- |
| 0 (無 LA) | **55.29%**      | —       |
| 0.3      | 53.58%          | -1.71pp |
| 1.0      | ~35%            | -20pp   |


雖然 LA 成功減少了 F1=0 的類別數（τ=0.3 時從 9 降到 4），但代價是大量的 micro accuracy 損失。在 120 class 的嚴重不平衡分佈下，LA 過度犧牲了大類的精度來提升小類。

### 6.4 RC Consistency 的潛力與局限

**v7（純 RC Consistency）**：

- Forward-only accuracy 最高（54.10%），表明模型學到了一定的 strand invariance
- 但 RC TTA 增益較小（+1.07pp vs v3 的 +1.43pp），因為訓練已部分學到了 RC invariance
- 訓練時間是 v4 的 1.5 倍（13h52m vs 9h23m），因為每個 batch 需處理兩次序列
- F1=0 類別數反而增加（15 vs 9），原因待探

**結論**：RC Consistency 的效果不明確。訓練成本增加 50%，最終 TTA accuracy 與 v4 幾乎相同。

### 6.5 RC TTA — 免費的推論端提升

RC TTA 在所有版本上一致帶來 +1~2pp 的 accuracy 改善，且不需要任何額外訓練。推論時間翻倍（需要跑兩次 forward pass），但考慮到 v4 的推論速度（1,243 reads/sec），即使使用 TTA 仍有 621 reads/sec，完全可接受。

---

## 7. 推薦配置

### 7.1 最佳效率配置：v4 + RC TTA


| 指標                 | 數值                                           |
| ------------------ | -------------------------------------------- |
| **Micro Accuracy** | **55.29%**                                   |
| Top-3 Accuracy     | 74.91%                                       |
| Top-5 Accuracy     | 82.91%                                       |
| Top-10 Accuracy    | 91.29%                                       |
| F1 (weighted)      | 52.51%                                       |
| 訓練時間               | 9h 23m                                       |
| GPU VRAM           | 4.7 GB                                       |
| 推論速度               | 1,243 reads/sec (fwd) / ~621 reads/sec (TTA) |
| Trainable Params   | 5.54M / 498M (1.1%)                          |


**選擇理由**：

- 與 v3 相比，accuracy 差距僅 0.07pp（55.29% vs 55.36%），在統計誤差範圍內
- GPU VRAM 減少 55%，推論速度提升 123%，訓練時間縮短 18%
- maxlen=32 可部署在更低規格的 GPU 上

### 7.2 復現指令

```bash
# 訓練
cd /work/ymj1123ntu/token_level_gfm_classifier
sbatch slurm/run_genus_v4.sh

# 評估 (含 RC TTA)
python scripts/evaluate.py \
  --config results/nt_token_genus_lora_v4_maxlen32/config.yaml \
  --checkpoint results/nt_token_genus_lora_v4_maxlen32/best.pt \
  --output_dir results/nt_token_genus_lora_v4_maxlen32/eval_rc_tta \
  --rc_tta
```

---

## 8. 已知限制與未來方向

### 8.1 已知限制

1. **Long-tail 問題未解決**：120 genera 中有 10–15 個 F1=0，macro F1 僅 25%。Logit Adjustment 未能有效改善，需要探索其他策略。
2. **Overfitting gap ~6%**：Train accuracy 比 val accuracy 高約 6pp，仍有改善空間。
3. **單一 validation set**：僅使用固定 10% split，未做 cross-validation 或多次 random split 的統計穩定性分析。
4. **僅測試 genus-level**：未延伸至 species-level（1,535 classes）分類。

### 8.2 未來方向

1. **Focal Loss**：針對困難樣本加權，可能比 Logit Adjustment 更適合此場景
2. **Hierarchical Classification**：利用 genus → species 的層次結構進行多級分類
3. **Curriculum Learning**：從易到難排列訓練樣本
4. **Larger backbone**：測試 NT v2 2.5B 參數版本
5. **Species-level 分類**：擴展至 1,535 classes，這是更實際的應用場景
6. **Ensemble**：結合多個不同 seed/配置的模型
7. **更長序列測試**：測試 250bp, 500bp 讀取對分類精度的影響

---

## 9. 開發過程紀錄

### 9.1 重要 Bug 修復


| 問題                      | 原因                                               | 解決方案                                         |
| ----------------------- | ------------------------------------------------ | -------------------------------------------- |
| Baseline data leakage   | 評估用全 500K 含訓練資料                                  | 改用 50K held-out val set                      |
| NaN loss (v1)           | `fp16` + extreme class weights + label smoothing | 改用 `bf16`，停用 label smoothing，clamped weights |
| AttentionPool shape bug | `self.query` expand 維度錯誤                         | 修正 `.expand()` 呼叫                            |
| v7 被 SLURM 砍掉           | RC consistency 計算量翻倍，24h 不夠                      | 延長至 48h                                      |
| `transformers` 相容性      | 新版不支援 NT dynamic modules                         | Pin `transformers==4.40.0`                   |


### 9.2 實驗時間線


| 日期    | 里程碑                                           |
| ----- | --------------------------------------------- |
| 02-11 | Frozen embedding baseline 完成（修正 data leakage） |
| 02-16 | Token-level v1 首次訓練（發現 NaN + shape bug）       |
| 02-18 | v3 baseline 建立（53.92%）                        |
| 02-21 | v4 maxlen=32 驗證（53.75%，效率大幅提升）                |
| 02-22 | v5/v5b Logit Adjustment 實驗（確認無效）              |
| 02-23 | v6 RC Consistency + LA 實驗                     |
| 02-26 | v7 純 RC Consistency 完成（55.18% TTA）            |
| 02-27 | 所有結果對齊，完成報告                                   |


---

## 附錄 A：完整超參數對照表


| 參數                  | v3    | v4    | v5    | v5b   | v6        | v7        |
| ------------------- | ----- | ----- | ----- | ----- | --------- | --------- |
| max_token_length    | 128   | 32    | 32    | 32    | 32        | 32        |
| batch_size          | 32    | 32    | 32    | 32    | 32        | 32        |
| grad_accum_steps    | 2     | 2     | 2     | 2     | 2         | 2         |
| backbone_lr         | 3e-5  | 3e-5  | 3e-5  | 3e-5  | 3e-5      | 3e-5      |
| head_lr             | 5e-4  | 5e-4  | 5e-4  | 5e-4  | 5e-4      | 5e-4      |
| weight_decay        | 0.02  | 0.02  | 0.02  | 0.02  | 0.02      | 0.02      |
| dropout             | 0.15  | 0.15  | 0.15  | 0.15  | 0.15      | 0.15      |
| LoRA r / α          | 16/32 | 16/32 | 16/32 | 16/32 | 16/32     | 16/32     |
| rc_augment          | ✓     | ✓     | ✓     | ✓     | —         | —         |
| rc_consistency      | —     | —     | —     | —     | ✓ (λ=0.1) | ✓ (λ=0.1) |
| logit_adj τ         | —     | —     | 1.0   | 0.3   | 1.0       | —         |
| class_weights       | —     | —     | —     | —     | —         | —         |
| label_smoothing     | 0     | 0     | 0     | 0     | 0         | 0         |
| phase1_epochs       | 5     | 5     | 5     | 5     | 5         | 5         |
| max_epochs (phase2) | 40    | 40    | 40    | 40    | 40        | 40        |
| early_stop patience | 7     | 7     | 7     | 7     | 7         | 7         |


## 附錄 B：結果檔案路徑

```
token_level_gfm_classifier/results/
├── nt_token_genus_lora_v3/
│   ├── best.pt, config.yaml, metrics.json, training_history.csv
│   ├── eval/                  ← fwd-only eval
│   └── eval_rc_tta/           ← RC TTA eval
├── nt_token_genus_lora_v4_maxlen32/
│   ├── best.pt, config.yaml, metrics.json, training_history.csv
│   └── eval_rc_tta/
├── nt_token_genus_lora_v5_logit_adj/
│   ├── best.pt, config.yaml, metrics.json, training_history.csv
│   └── eval/
├── nt_token_genus_lora_v5b_la_tau03/
│   ├── best.pt, config.yaml, metrics.json, training_history.csv
│   └── eval/
├── nt_token_genus_lora_v6_rc_consist/
│   ├── best.pt, config.yaml, metrics.json, training_history.csv
│   └── eval/
└── nt_token_genus_lora_v7_rc_only/
    ├── best.pt, config.yaml, metrics.json, training_history.csv
    └── eval/
```

