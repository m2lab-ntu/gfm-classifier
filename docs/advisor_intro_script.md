# 共同指導老師專案介紹 — 逐字稿

目標：完整介紹專案從問題定義到目前進度，涵蓋架構、實驗歷程、核心發現、遇到的困難、值得討論的開放問題。

預計時長：40–60 分鐘。

---

## Slide 1 — Title

老師好，今天這份報告是把整個專案從頭到尾做一次完整的介紹。前面會花點時間講 background 跟系統設計，讓老師了解整個架構的來龍去脈；中段是實驗結果和主要發現；最後幾張是目前還在跑的東西以及我覺得值得跟老師討論的幾個方向。

---

## Slide 2 — 大綱

今天大致分成七個部分：

1. 專案背景與問題定義
2. 相關背景知識（GFM、tokenization、LoRA）
3. 系統架構與關鍵設計決策
4. 實驗歷程（genus 和 species）
5. 核心發現（資料規模、tokenization、hierarchical）
6. 目前進行中的實驗
7. 遇到的困難與值得討論的開放問題

---

## Slide 3 — Section：專案背景與問題定義

先從我們要解決的問題講起。

---

## Slide 4 — 問題定義

我們要做的是 **宏基因體 (metagenomic) taxonomic classification**：

- **Input**: 單條 150bp 的 DNA short read（模擬 Illumina paired-end sequencing）
- **Output**: 該 read 所屬的 genus（120 類）或 species（1535 類）
- **資料來源**: HGR-UMGS — 2,505 個人類腸道宏基因體的參考基因體
- **模擬流程**: ART Illumina simulator 從參考基因體生成約 258M reads，再做類別平衡 subsample 到 5M / 50M

重點是：這個任務**不是整條基因體分類，而是單條 150bp read 分類**。這讓問題本質變得非常 hard —— 一條 read 只佔一個 genome 的百萬分之一，能看到的序列 context 極度有限。

---

## Slide 5 — 為什麼這個問題難

四個主要難點：

1. **Short reads 資訊量少**：150bp 對應 25 個 6-mer token 或 145 個 overlapping 6-mer，相對於一個 3Mbp 的細菌 genome 資訊密度極低
2. **類別數量大**：species level 1535 類，random baseline 只有 0.065%
3. **長尾分布**：即使 balanced subsample，仍有許多 species 樣本遠少於主流類別
4. **近緣物種難分**：同 genus 內的 species 序列高度相似，甚至 100bp 以上完全相同，靠短片段很難區分

這些讓我們的任務跟常見的 DNA task（promoter prediction、splice site 這類）很不一樣 —— 我們需要 fine-grained discrimination over **large class space** with **very short context**。

---

## Slide 6 — Section：相關背景知識

接下來快速過一下幾個核心 background，讓老師理解後面架構選型的理由。

---

## Slide 7 — Genomic Foundation Models (GFMs)

GFM 的概念類比 NLP 的 BERT/GPT：用大量未標註的基因體序列做 self-supervised pre-training，讓模型學到 DNA 的「語言結構」—— motif、codon bias、regulatory elements 等。

代表模型有三代演進：

- **DNABERT (2021)**: BERT-base, 86M params, overlapping 6-mer (stride=1)
- **Nucleotide Transformer v2 (2024)**: 500M params, non-overlapping 6-mer (stride=6)
- **DNABERT-2 (2023)**: MosaicBERT, 117M params, **BPE (learned tokenization)**

下游任務過去主要集中在人類基因調控相關的任務。宏基因體分類是相對較新的應用場景，文獻還不算成熟。

---

## Slide 8 — Nucleotide Transformer v2（我們主要用的 backbone）

我們選 NT-v2 作為主要 backbone 的原因：

- **多物種預訓練**：在 850 個物種的基因體上訓練，涵蓋 bacteria、archaea、eukaryote
- **規模最大**：500M params（其他公開 GFM 多為 100M 等級）
- **產業支持**：InstaDeepAI（後來被 BioNTech 收購）持續維護
- **Tokenization**: non-overlapping 6-mer, stride=6 → 150bp = 25 tokens

重要細節：NT-v2 的 tokenizer **把 4^6 = 4096 個 6-mer 各自當作一個 token**。這個設計決策會在後面發現中變成一個關鍵討論點。

---

## Slide 9 — LoRA (Low-Rank Adaptation)

Fine-tune 500M 參數的 full model 在單張 GPU 上不太可行，我們用 LoRA：

- 只在 attention 的 Q, K, V 矩陣上加 low-rank delta（r=16）
- **Trainable params: 5.54M，約總參數 1.11%**
- Backbone 的 pre-trained 權重凍結，只有 LoRA adapters + classification head 更新

好處是省記憶體、訓練快、避免 catastrophic forgetting。代價是表達能力受限於 low-rank constraint —— 如果下游任務跟 pre-training domain 差異極大，LoRA 可能不夠，full fine-tune 才能突破。

---

## Slide 10 — Reverse Complement (RC) 對稱性

DNA 雙股螺旋：一股 `ACGT...` 對應另一股的反向互補 `...ACGT`（A↔T，C↔G）。Sequencing 時正反股隨機測到，兩者是**同一個生物學單位**。

但 Transformer 本身**不是 RC-equivariant**：對模型而言，`ACGT` 和它的 RC `ACGT`（反向互補）是兩個不同的 input。這是一個已知的 inductive bias 缺失。

我們用三種機制處理：

1. **RC augmentation (train)**：訓練時 50% 機率把 read 翻成 RC
2. **RC TTA (inference)**：預測時 `ŷ = argmax[logits(s) + logits(RC(s))]`
3. **RC consistency loss (optional)**：`λ·KL(forward ∥ RC)`，鼓勵兩邊預測一致

RC TTA 是 **free lunch**：不用重訓，直接在 inference 時多做一次 forward 就有 +1~2pp 的提升。

---

## Slide 11 — Section：系統架構

現在進到我們自己的設計。

---

## Slide 12 — Pipeline 整體流程

從 input 到 output 的完整 pipeline：

```
150bp DNA read
  ↓  6-mer tokenization (stride=6)
25 token IDs
  ↓  NT-v2 backbone (29 layers, 1024 hidden, LoRA on Q/K/V)
25 × 1024 token embeddings  ← 保留整個 token sequence
  ↓  4-head AttentionPool classification head
1024-dim pooled representation
  ↓  MLP (2 layers, 512 hidden, dropout 0.15)
120 logits (genus) / 1535 logits (species)
```

**關鍵設計決策：保留 token sequence，不做 mean pooling**。這跟先前 phase 1 的 frozen embedding baseline 最大的差別。

---

## Slide 13 — 為什麼不 mean pool？

先前 phase 1 的方法：backbone → mean pool → 1024-dim vector → MLP classifier。

問題：mean pool 把 25 個 token 的資訊全部平均，讓 downstream classifier 看不到 local pattern。

Token-level 的 AttentionPool head：

- 保留 25 × 1024 完整 sequence
- 4-head attention 讓模型自己學哪些 token 重要
- 類似 CLS token 機制但不依賴特定位置

實驗證實：同樣 backbone 同樣訓練設定，token-level 比 mean-pool 高 ~8pp genus accuracy。

---

## Slide 14 — 兩階段訓練策略

**Phase 1 (optional)**：凍結 backbone，只訓練 head —— 避免一開始大梯度破壞 pre-trained 權重。

**Phase 2**：解凍 LoRA，head 和 LoRA 同時訓練，用 **differential learning rate**：

- Head LR: `5e-4`（需要從 random init 快速收斂）
- Backbone LR (LoRA): `3e-5`（已經 pre-trained，小幅調整即可）

LR schedule：cosine with warmup (5%)，early stopping patience=5。

---

## Slide 15 — 資料設計

- 原始資料：258M reads，來自 2,505 個 human gut 細菌 genomes（HGR-UMGS）
- 使用 ART Illumina simulator 生成 150bp paired-end reads
- 類別平衡 subsample：5M / 50M 兩個版本（由 `subsample_balanced.py` 生成）
- Train/Val split：90/10，seed 固定以保證可重現
- Data augmentation：training 時 50% RC flip

Genus 有 120 類，species 有 1535 類（filter 過至少 N 個 reads 的 species）。

---

## Slide 16 — Section：實驗歷程

接下來進到實驗本身。先講 genus task，再講 species task，最後是 hierarchical evaluation。

---

## Slide 17 — Genus 實驗演進（v4 → v11）

| Version | Data | 重點 | Val Acc (RC TTA) |
|---------|------|------|------------------|
| v4 | 500K | 基本架構 | 55% |
| v5 | 500K | + Logit Adjustment (τ=0.3) | ~55.5% |
| v6 | 500K | + RC Consistency (λ=0.1) | ~55.2% |
| v7 | 500K | RC Consistency only | ~55.3% |
| **v8** | **5M** | basic, 10× data | **63.05%** |
| **v9** | **50M** | basic, 100× data | **67.07%** |
| v11 | 50M | Shallow Transformer (ablation) | ~36% |

**核心觀察**：任一 training trick (logit adj / RC consistency / class weighting) 只有 ±0.5pp；資料量 500K → 5M +8pp，5M → 50M 再 +4pp。

---

## Slide 18 — 核心發現一：資料量 >> Training Tricks

這張是我覺得這個專案**最重要的 takeaway**：

- 做了大量 training trick 的排列組合（logit adjustment、RC consistency、sampler、class weighting、label smoothing 等）
- 沒有任何單一 trick 貢獻超過 1pp
- 但單純把資料從 500K 加到 50M：**+12pp**

這跟近年大 LLM 領域的 scaling law 觀察一致。對我們研究生而言，它的實務意涵是：**花時間做 data scaling 和 data cleaning 的 ROI，遠大於微調 loss / sampler / regularizer**。

---

## Slide 19 — RC TTA：Free Lunch

RC TTA 實測結果：

| Task | Forward only | + RC TTA | Δ |
|------|--------------|----------|---|
| Genus (v9, 50M) | 66.29% | **67.07%** | +0.78pp |
| Genus top-3 | 83.85% | 84.40% | +0.56pp |
| Genus top-10 | 95.02% | 95.25% | +0.23pp |

代價：inference time × 2。但因為 genus task 在我們環境 5168 reads/sec，變 2584 reads/sec 對實際使用影響不大。

**為什麼 RC TTA 有效**：model 對 forward 和 RC 的 prediction 有互補的 error pattern，average 相當於 strand ensemble。更深的 theoretical justification 寫在 thesis §2.7。

---

## Slide 20 — Species 任務 (1535 類)

Species 是比 genus 困難數個等級的任務。Sp_v4 (50M) 目前收斂到 val_acc ~17.5%，看似低但 random baseline 是 0.065% —— 相對提升是 270×。

我們探討了六種 evaluation mode 來理解 species 分類的 failure mode：

| Mode | Top-1 | Top-5 | F1-macro | F1=0 classes |
|------|-------|-------|----------|--------------|
| **Flat classifier** | 16.4% | 46.7% | 0.137 | 804 |
| Hard top-5 genus routing | 16.5% | 46.1% | 0.139 | ~ |
| Soft genus routing | 16.2% | 46.2% | 0.135 | ~ |
| **Oracle genus** | **27.9%** | 65.3% | 0.256 | ~ |
| Per-genus (predicted genus) | 11.2% | 32.9% | 0.109 | 401 |
| Per-genus (oracle genus) | 21.8% | 60.2% | 0.204 | 362 |

---

## Slide 21 — 核心發現二：Genus 是 Species 的 Bottleneck

**Oracle genus (27.9%) − Flat (16.4%) = +11.5pp**

這個 gap 告訴我們：**如果 genus 永遠對，species 可以再多 11.5pp**。反過來說，目前 species 錯誤中有接近一半是被 genus 層錯誤連帶拖下去的。

但 top-k genus routing（hard/soft）**完全沒有實質提升**（±0.3pp）。為什麼 oracle 這麼強，實作的 routing 卻無效？

推測：genus model 和 species model 的預測在邊界 case 上有衝突，而目前簡單的 combine strategy（top-k mask 或機率乘法）無法妥善解決衝突。老師這邊如果有建議會很有用。

---

## Slide 22 — 核心發現三：Per-Genus 幫助長尾

Per-genus 是 hierarchical 的另一種實作：每個 genus 訓練一個專屬 species classifier。

- 81 個多物種 genera 各訓練一個 model（39 個單物種 genera 直接 deterministic）
- Backbone 凍結 NT-v2，只訓練 attention head
- 5M 資料分配到每個 genus 後約 ~3,260 reads/species

結果比 flat 差（21.8% vs 27.9% oracle），原因是**每個 genus 得到的資料量比 flat 少一個數量級**。

但 **F1=0 的 species 從 804 降到 362/401**，代表 per-genus **對長尾分類有實質幫助** —— 罕見 species 在 flat model 裡被 head class 壓過，但在 per-genus 的小分類空間裡有機會被看見。

---

## Slide 23 — 核心發現四：Pre-training 在 Matched Tokenization 下顯著勝出

MetaTransformer（MT）是我們的對照組：shallow Transformer from scratch，刻意沒有 pre-training，用來隔離 tokenization 變數。

**在 NT-v2 相同的 tokenization 設定 (k=6) 下，我們的 NT-v2+LoRA 大幅勝出：**

| Model | Tokenization | Genus Acc | Δ vs NT-v2 |
|-------|--------------|-----------|------------|
| **NT-v2 + LoRA (ours, RC TTA)** | 6-mer non-overlap (stride=6) | **67.07%** | — |
| MetaTransformer (from scratch) | 6-mer non-overlap (stride=6) | ~36% | **−31pp** |
| MetaTransformer (from scratch) | 6-mer overlap (stride=1, 6× tokens) | 48.87% | **−18pp** |

**這證實三件事：**

1. **Pre-training 的 representation quality 是 real，不是被 tokenization 取代** — 同 k=6 下 +31pp
2. 就算 MT 改成 overlap stride=1 讓 token 數量變 6 倍，仍落後 18pp —— 資訊密度不能替代 pre-trained inductive bias
3. 我們的 pipeline (NT-v2 + LoRA + AttentionPool + RC TTA) 在合理的 token budget 下是 SOTA setting

---

## Slide 24 — MetaTransformer 的高 k 設定：用 Vocab Size 換 Accuracy

MT 唯一超越 NT-v2 的設定是 k=12, 13 overlap，但代價是 vocab 規模暴增：

| k | stride | Theoretical vocab (4^k) | Genus Acc |
|---|--------|-------------------------|-----------|
| 6 | 6 (non-overlap) | 4,096 (matches NT-v2) | ~36% |
| 6 | 1 (overlap) | 4,096 | 48.87% |
| 12 | 1 (overlap) | **16.7 M** | 78.83% |
| 13 | 1 (overlap) | **67 M** | 87.42% |
| 13 | 13 (non-overlap) | 67 M | 27.30% |

**解讀：**

- NT-v2 vocab 只有 4,104，hidden 1024 → embedding 約 4M params
- MT k=13 theoretical vocab 67M —— 光 embedding table 本身就遠大於 NT-v2 整個 backbone
- **等於直接把 k-mer → label 的對應「背」在 embedding 裡**，不是架構層面的勝利
- 沒有 pre-training 的 model 只能靠更大的 k 把資訊塞進 embedding table

**這給論文的方向性 insight**：

- Pre-training 在 small vocab (k=6) 下是關鍵
- High-k tokenization 若搭配 pre-training（目前文獻沒有），理論上應該同時享受兩邊優勢 —— 這是 future work 的主要方向

---

## Slide 25 — Section：目前進行中的實驗

上次討論老師建議思考「能否突破 NT-v2 tokenization 限制」，這是那個方向的具體後續。

---

## Slide 26 — 新一輪 Tokenization 對比實驗

兩個已送的 jobs（genus task, 5M 資料）：

**DNABERT (2021)**

- backbone: `zhihan1996/DNA_bert_6`
- 86M params
- **overlapping 6-mer (stride=1)** — 跟 NT-v2 只差 stride
- 目的：隔離 stride 變數，其他維持 k=6

**DNABERT-2 (2023)**

- backbone: `zhihan1996/DNABERT-2-117M`
- 117M params, MosaicBERT 架構
- **BPE (learned tokenization)**
- 目的：測試 learned tokenization 能否贏 fixed k-mer

---

## Slide 27 — Controlled Comparison 的限制

嚴格講，這三個 model 並非 fully fair comparison：

| Model | Params | Tokenization | Hidden dim |
|-------|--------|--------------|------------|
| NT-v2 | 498M | non-overlap 6-mer | 1024 |
| DNABERT | 86M | **overlap 6-mer** | 768 |
| DNABERT-2 | 117M | **BPE** | 768 |

參數量差距高達 5.8×。但在這組設定下：

- 如果 DNABERT (86M) > NT-v2 (498M) → **stride 效應壓過 model scale 效應**，非常強的結論
- 如果 DNABERT-2 (BPE) > DNABERT (6-mer) → learned tokenization > fixed k-mer

論文會清楚標注 param count 差異。

---

## Slide 28 — 論文中其他已完成的實驗設定

除了主 pipeline，thesis 還涵蓋：

- **Shallow Transformer ablation (v11)**：證實 pre-training 有用（v9 - v11 gap ≈ 31pp）
- **Logit Adjustment, RC Consistency sweeps**：負面結論，寫入 thesis 展現我們做過嚴謹 ablation
- **Per-genus pipeline**：實作、訓練 81 個小 model、eval
- **RC TTA theoretical justification**：thesis §2.7 strand-symmetry derivation

---

## Slide 29 — Section：遇到的困難

---

## Slide 30 — 技術性挑戰

這段是讓老師知道我們大概解決過哪些非 trivial 的技術問題：

1. **PyTorch 2.6 breaking change**：`weights_only=True` 變預設，checkpoint 裡有 numpy scalar 會爆 → 修改所有 `torch.load` 加 `weights_only=False`
2. **TWCC SLURM 48h timeout**：v9、sp_v4 都卡在 48h → 寫 auto-resume 腳本（偵測 `last.pt` 自動 `--resume`）
3. **Eval OOM at 128G**：5M val × 1535 species logits ≈ 30GB × 多份 buffer 超過 memory → 升級 200G (TWCC normal partition 上限)
4. **DNABERT `trust_remote_code` 衝突**：custom BertConfig 撞 stock BertConfig → 把 `trust_remote_code` 變成 config 可控欄位
5. **Per-genus sequential 訓練 GPU 只用 5%**：平行化 (N=4 concurrent) 從 3h 縮到 30 分鐘

---

## Slide 31 — 方法論上的挑戰

1. **Fair comparison 怎麼做**：DNABERT (86M) vs NT-v2 (498M) 參數量差 5.8×，怎麼在不完美對照下支持 tokenization 結論
2. **Hierarchical 的 routing 策略**：為什麼 oracle 27.9% 但 top-k 完全失效？
3. **長尾分類的 trade-off**：per-genus 提升長尾 F1 但整體 top-1 下降，誰該被優先
4. **實驗設計要交給 ablation matrix 還是 single-variable 測**：time budget 有限下如何取捨

---

## Slide 32 — Section：值得討論的開放問題

---

## Slide 33 — 開放問題清單

這是我覺得最需要老師一起討論的幾個方向：

1. **高 k + pre-training 的 GFM 是否值得 pursue？** Matched tokenization 下 NT-v2 遠勝 MT；但 k=13 + embedding 硬背仍能達 87%。兩者結合在理論上應能同時享受 pre-training 與 high-k 優勢
2. **DNABERT / DNABERT-2 的 5M 結果 (running)** 會決定論文第二個主要 finding：overlap stride 或 learned BPE 帶來的提升是否在 matched scale 下 significant
3. **Per-genus vs top-k routing 哪個該走下去？** Oracle 顯示 top-k 潛力高，但實作看 per-genus 對長尾 F1 有幫助，策略選擇影響論文 species section 定位
4. **RC-equivariant 架構（Caduceus 類）** 能否取代 RC TTA、免掉 2× inference cost？對我們專案 worth trying 嗎？
5. **Metagenomic-specific pre-training (METAGENE-1, 7B)** 在有限資源下是否仍可作為 upper-bound reference？
6. **論文 narrative 定位**：核心敘事可以是「Pre-trained GFM 在正確 setting 下 state-of-the-art，而 tokenization 是影響力被低估的獨立變數」。想聽老師對這個定調的意見

---

## Slide 34 — 目前專案狀態

- **Code**: `/work/ymj1123ntu/token_level_gfm_classifier`（尚未 git 化，待做）
- **Thesis**: `/work/ymj1123ntu/thesis`，Chapter 2/4/5 約 75% 完成
- **Running jobs**:
  - sp_v4 species full eval（174794, 剩 1-2h）
  - DNABERT 5M genus（175206）
  - DNABERT-2 5M genus（175207）
- **預計 ~10-12h 內所有目前 pending 實驗完成**
- **下一里程碑**：完成 tokenization comparison 分析、更新 thesis Chapter 4

---

## Slide 35 — Thank you

以上就是完整的專案進度。感謝老師的時間，接下來想聽聽老師的建議跟討論。
