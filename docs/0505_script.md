# 0505 Weekly Progress — 逐字稿

---

## Slide 1 — Title

（直接進下一張）

---

## Slide 2 — This Week's Highlights

本週主要有四件事。

第一，per-genus 50M LoRA 的 81 個分類器全部訓練完並評估完畢。最重要的結果是：在 oracle genus routing 的條件下，per-genus 模型的 Top-1 達到 27.8%，超越了整體 sp_v4 模型的 oracle 上限 27.4%，這代表我們的 hierarchical 架構方向是對的，per-genus 專門訓練確實有效。

第二，我們修正了評估方法。之前用的 100K 測試集和訓練集有 99% 重疊，改成用 MetaTransformer 的 val_reads.fa 抽樣的獨立測試集之後，數字差距不到 0.5%，確認模型沒有 overfit，只是之前的評估方法不夠嚴謹。

第三，bottleneck 很清楚：genus model 的準確度 66.1% 導致 predicted routing 反而比不 routing 還差，14.7% 對上 15.9%。主要問題集中在 5 個大 genus，Collinsella、Clostridium、Prevotella、Bacteroides、Blautia，這幾個每個 genus 裡面都有幾十到幾百個 species，非常難分。

第四，因此下一步計畫是對這 5 個大 genus 加入第三層 routing，也就是 subgenus 分層。

另外 thesis 這邊，chapter 4 全部已經更新到最新結果，目前 117 頁。

---

## Slide 3 — Section: Per-genus 50M

---

## Slide 4 — Per-genus 50M Training Results

我們訓練了 81 個 per-genus 分類器，每個負責自己 genus 底下的 species 分類，backbone 是 frozen 的 NT-v2，只訓練 attention pooling head，用 50M 的資料。39 個 single-species genus 不需要分類器，直接 deterministic。

整體來說 mean val_acc 是 48.3%，中位數 44.2%。但準確度非常依賴 species 數。5 個 species 以下的 genus 平均超過 80%，問題不大。超過 50 個 species 的 genus 平均不到 20%，幾乎沒辦法用。

最難的 5 個是：Collinsella 有 349 個 species，val_acc 只有 1.3%，幾乎是亂猜。Clostridium 191 個 species，19.9%。Prevotella 91 個 26.6%，Bacteroides 79 個 15.9%，Blautia 大概 60 個。

這幾個 genus 就是整個 hierarchical pipeline 的瓶頸所在。

---

## Slide 5 — Section: Hierarchical Evaluation

---

## Slide 6 — 主結果表

這是本週最重要的一張表，用獨立測試集跑的結果。

上半部是 sp_v4 搭配不同 routing 的結果。Flat baseline 15.9%，Top-5 routing 和 soft routing 幾乎沒有變化，跟之前的分析一致，routing 幫助有限。Oracle genus 給 27.4%，這是 sp_v4 的理論上限。

下半部是 per-genus 50M 的結果。Predicted routing，也就是用 v9 genus model 決定要用哪個 per-genus 分類器，結果是 14.7%，比 flat baseline 15.9% 還差。但 oracle genus，也就是用真正的 genus label 去 routing，結果是 27.8%，**比 sp_v4 oracle 27.4% 還高**。

這個 27.8% 超越 27.4% 這件事很重要。它代表 hierarchical 架構本身是對的，per-genus 專門訓練確實比整體模型更懂每個 genus 裡面的 species 差異。問題不在架構，問題在 genus routing 的準確度。

---

## Slide 7 — 分析

為什麼 per-genus predicted routing 比 sp_v4 routing 還差這麼多？

sp_v4 加 routing 的時候，就算 genus routing 錯了，logit 只是被 re-weight，還有一些訊號保留下來，所以影響有限，大概 ±0 pp。

但 per-genus 加 routing，一旦選到錯誤的 genus model，那個 model 根本不認識正確的 species，所有 output 都是針對錯 genus 的 species，準確度直接趨近於零。我們有 33.9% 的 read 被送去錯的 genus model，這個損失很難補回來。

但 oracle 的分析讓我們看到潛力。如果 genus accuracy 能到 80%，理論上 pipeline 可以達到 22% 以上，比現在的 flat baseline 高 6 pp。如果到 90%，可以到 25%，比 baseline 高 9 pp。所以方向是對的，就是 genus accuracy 要更高。

---

## Slide 8 — MT Sample-Level Comparison

這邊補一個跟 MetaTransformer 的 sample-level 比較。

我們用同一套評估 pipeline，對三個模型都跑了一遍：NT-v2 v9 67% 準確度、MT 6-mer stride=1 49%、MT 13-mer stride=1 87%。

在 abundance estimation 這件事上，三個模型的差距其實沒那麼大。我們的 Pearson r 是 0.993，MT 13-mer 是 0.999，差距很小。原因是 misclassified 的 read 在 sample level 會互相抵銷——分錯的 read 散布到很多 genus，不會集中在哪一個，所以 aggregate 的時候大部分誤差會消掉。

但在 binary detection 這件事上，差距就很明顯。ROC AUC 我們是 0.705，MT 13-mer 是 0.900，差很多。在 95% specificity 的操作點，我們的 sensitivity 是 17.2%，MT 13-mer 是 47.7%。

為什麼 detection 的差距比 abundance 大這麼多？因為 detection 有 noise floor 的問題。一個 absent genus 在 50K reads 的 sample 裡面，expected 會收到大約 50000 × 33% / 120 ≈ 138 個 misclassified reads，對應 0.28% 的 spurious abundance。但 87% accuracy 的模型只有 0.11%。Detection threshold 要設在 noise floor 以上，threshold 越高，低 abundance 的 genus 就越難偵測到。

這個分析說明：提高 per-read 準確度對 detection 的幫助比 abundance estimation 大很多，是非線性的關係。

---

## Slide 9 — Section: Subgenus 3-Layer Routing

---

## Slide 9 — Subgenus 架構

有兩條路可以提升 predicted routing 的準確度：一是提升 genus model 本身的準確度，但這受限於 NT-v2 的 6-mer tokenization，很難繞過去。二是針對最難的 per-genus model 做改善，也就是 subgenus routing。

計畫是這樣：對最難的 5 個大 genus，在 genus model 和 per-genus model 之間再加一層 subgenus router。

Genus model v9 維持不動，所有現有的 per-genus model 維持不動，只針對這 5 個加第三層。

具體做法是把每個大 genus 的 species 分成 25 到 30 個一組，Collinsella 349 個 species 大概分 12 組。每組訓練一個獨立的 per-subgenus 分類器。這樣每個分類器只要面對 25–30 個 class，比起 349 個容易多了。

實作上需要新增三個東西：split_subgenus.py 產生分組 mapping，gen_subgenus_configs.py 自動生成訓練 config，然後修改 evaluate_per_genus.py 加入第三層 routing 邏輯。train.py 完全不需要動，沿用現有的即可。

---

## Slide 10 — Expected Outcome & 決策點

預期 subgenus routing 可以把這 5 個大 genus 的準確度從目前的 1–27% 拉高到每個 subgroup 40–50%+。整體 predicted routing 估計可以從 14.7% 提升到 18–20% 左右，超越 flat baseline 的 15.9%，讓 hierarchical pipeline 真正 end-to-end 有效。

時間上大概 3 到 5 天：實作加上在 TWCC 跑完訓練和評估。

這邊有一個決策點想請教老師：

Option A 是現在做 subgenus routing，結果出來後加進 thesis 再 submit。這樣 story 更完整，pipeline 真的 end-to-end 有效。

Option B 是現在就 submit，把 subgenus routing 列為 future work。

目前的核心 claim 已經站得住腳：per-genus 50M oracle 27.8% 超越 sp_v4 oracle 27.4%，hierarchical 架構方向正確，而且 genus accuracy 是主要瓶頸這件事有清楚的定量分析。所以 Option B 也不是沒辦法。

---

## Slide 11 — Section: Thesis & Overall Status

---

## Slide 12 — Thesis Status

Thesis 目前 117 頁。Chapter 2 背景和 Chapter 3 方法已經完成。Chapter 4 實驗結果這週更新了幾個部分：

Data scaling 的 v9 final number 全部更新到 epoch 30 的結果；hierarchical evaluation 這節換成用獨立測試集的新數字，per-genus 50M 的結果也都進去了。

目前待補的只剩一個：如果 subgenus routing 有做，§4.15 那節才需要寫。Chapter 5 conclusion 和 abstract 都已經完成。

後續就是等 subgenus 結果（或決定不做），final proofread，然後 submit。

---

## Slide 13 — Publication Venues

這邊也想跟老師討論一下投稿方向。我有問過共同指導的陳子鋐老師，他說他忍不住想從最難的開始試，第一選擇推薦 **Nature Computational Science**，備案推薦 **Communications Biology**，說這個應該比較容易進。

國際會議的話，他說要看時程，而且重點是要有人能去現場。

所以想請教劉老師您的看法：以目前的結果，哪個 venue 比較合適？期刊和會議的優先順序怎麼安排比較好？

---

## Slide 14 — Complete Experiment Results

（備用 slide，有問到再翻到這頁回答）

這是所有做過的實驗的完整結果整理，從 genus 分類、tokenization ablation、species 分類、hierarchical pipeline 到 sample-level 評估，方便對照。

---
