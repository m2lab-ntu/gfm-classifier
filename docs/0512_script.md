# 0512 Weekly Progress — 逐字稿

---

## Slide 1 — Title

（直接進下一張）

---

## Slide 2 — This Week's Highlights

本週主要有兩件大事，加上一個我想跟老師討論的方向。

第一，subgenus routing 這週完整跑完，結果是 negative。Hard routing 準確度從 14.7% 掉到 13.2%，soft routing 也只回到 13.6%，兩種都比 baseline 還差。就算在 oracle genus 條件下也一樣，從 27.8% 掉到 25.6%，代表問題不是 genus routing 準不準，而是 NT-v2 的 embedding 根本無法分開同屬裡的 species。這個 negative result 我覺得非常重要，等一下會詳細說。

第二，因為這個結果，我們所有計畫的實驗現在都跑完了。Thesis 也同步更新，新增了 §4.12.7 這一節記錄 subgenus routing 的分析和 negative result，現在是 121 頁，整個故事是完整的。

第三，今天我想跟老師討論的是：我認為現在已經可以準備收工、投稿，我有幾個具體的點想請老師評估。

---

## Slide 3 — Section: Subgenus Routing

---

## Slide 4 — Recap & Hypothesis

先快速 recap 一下 0505 的狀況。上週我們確認 per-genus 50M 在 oracle genus routing 下可以達到 27.8%，超越 sp_v4 的 27.4%，hierarchical 架構方向是對的。但 predicted routing 只有 14.7%，比 flat baseline 15.9% 還差。

問題集中在 5 個大 genus：Collinsella 有 349 個 species，val accuracy 只有 1.3%，幾乎是亂猜；Clostridium 191 個，19.9%；Prevotella 91 個，26.6%；Bacteroides 79 個，15.9%。

所以這週的假說是：如果我們在 genus model 和 per-genus classifier 中間加一層，把大 genus 的 species 切成 25–30 個一組，每組訓練一個更小的 classifier，問題應該就變得更可處理。理論上 predicted routing 應該可以從 14.7% 提升到 18–20%，超越 flat baseline。

---

## Slide 5 — Embedding Analysis

在跑完整 routing 之前，我先做了一件事：用 NT-v2 的 embedding 對 Collinsella 的 species 做 K-means clustering，看看 embedding space 裡面有沒有可以分群的結構。

結果是：silhouette coefficient 0.03，接近 0，代表幾乎沒有 cluster 結構。UMAP 的視覺化也確認這件事：349 個 species 在 embedding space 裡面就是一個連續的、分不開的 blob，完全看不出哪些 species 應該被歸在一起。

這就代表說，不管怎麼切，K-means 切出來的 subgenus partition 都是沒有生物學意義的任意分組。每一組裡面的 species 在 embedding space 裡是隨機分散的，不是真的在一個 cluster 裡面。

這個分析其實已經預告了 routing 會失敗——但我們還是跑了完整的實驗來確認。

---

## Slide 6 — Routing Results

這是結果表。

Baseline 是 per-genus 50M，predicted routing 14.7%，oracle routing 27.8%。

Hard subgenus routing：predicted 掉到 13.2%，少了 1.5 pp；oracle 也掉到 25.6%，少了 2.2 pp。

Soft routing 稍微好一點，predicted 13.6%，oracle 26.1%，但還是比 baseline 差。

注意一個特別重要的地方：就算是 oracle genus routing，也就是我們告訴模型正確的 genus，subgenus routing 還是讓準確度下降。這代表問題不是出在 genus routing 不準，而是 subgenus partition 本身是錯的——我們把 species 切到不對的 subgroup，反而增加了一個新的 routing error source，沒有任何好處抵銷它。

---

## Slide 7 — What This Means

這個 negative result 告訴我們什麼？

最重要的一點：瓶頸是表示層，不是路由架構的深度。NT-v2 的 non-overlapping 6-mer tokenizer 無法在 embedding 層面區分同屬的 species，所以不管加多少層路由，都解決不了這個問題。

這跟我們之前做 tokenization ablation 的結論完全一致。MT 13-mer stride=1 從頭訓練可以達到 87.42%，比 NT-v2 + LoRA 高 20.35 pp，原因就是 overlapping 13-mer 有辦法捕捉更細緻的局部序列特徵，NT-v2 的 6-mer 做不到。

所以改善方向是：換掉 tokenizer，用 overlapping long-k tokenization 預訓練一個新的微生物 GFM，而不是在現有 NT-v2 框架上加路由層。

Negative result 不是壞事。它讓我們確定地排除了一個方向，讓 future work 的建議更聚焦、更有說服力。

---

## Slide 8 — Section: Complete Experiment Overview

---

## Slide 9 — All Experiments Map

這張是我們所有做過的實驗的完整整理。

上半部是 NT-v2 框架的一系列實驗：從 frozen baseline，到 token-level + LoRA，到不同規模的資料（500K 到 50M），到跟 DNABERT、DNABERT-2 的比較，到 backbone ablation，到 hierarchical pipeline，再到這週的 subgenus routing。

下半部是 tokenization ablation：MetaTransformer 用相同的 50M 資料，從 6-mer non-overlap 一路到 13-mer stride=1，每一步都有清楚的提升。

兩個主要的跨步：
- pre-training 的貢獻：在固定 6-mer tokenization 下，NT-v2 比 random init 多 13.19 pp。
- tokenization 的貢獻：MT 13-mer 比 NT-v2 + LoRA 多 20.35 pp，在沒有 pre-training 的情況下。

這張圖就是整個 thesis 的實驗空間。

---

## Slide 10 — The Complete Story

我覺得這個故事的好處是它是一個 falsifiable chain of evidence，每個 claim 都有對應的 controlled experiment。

Step 1：資料量是 NT-v2 框架內最重要的因素。500K 到 5M 加了 7.76 pp，5M 到 50M 再加 4.02 pp，任何架構 trick 都不超過 ±0.5 pp。

Step 2：Pre-training 在固定 tokenization 下有幫助。29 層的 NT-v2 比 1 層的 random init 多了 13.19 pp，驗證了 GFM pre-training 的價值。

Step 3：Tokenization 在跨架構比較下是更大的因素。MT 13-mer 沒有 pre-training，但比有 pre-training 的 NT-v2 多了 20.35 pp。這是這篇論文最重要的 finding。

Step 4：Hierarchical 架構方向正確。Per-genus oracle 27.8% 超越 sp_v4 oracle 27.4%。

Step 5：Subgenus routing 無法突破瓶頸。Silhouette 0.03，所有 routing 策略都讓準確度下降，確認問題在表示層。

這五步構成一個完整的、自洽的故事，每一步都可以被實驗反駁，但都沒有被反駁。

---

## Slide 11 — Section: Status & Publication Plan

---

## Slide 12 — Thesis Status

Thesis 現在 121 頁，五章都完成了。

Chapter 3 這邊加了 ART 的完整 simulation 參數、reproducibility audit、data split 的說明。Chapter 4 本週新增了 §4.12.7 subgenus routing negative result 這一節。Chapter 5 的 future work 也同步更新，hierarchical routing improvements 那節改成說明 subgenus routing 失敗的原因，並重新指向 long-k pre-training 的方向。

所有實驗都跑完，thesis 的內容是完整的。

---

## Slide 13 — Why Ready to Publish

我想說明為什麼我認為現在是可以投稿的時機。

研究問題已經有完整的答案：Q1 token-level vs mean-pool，答案是 yes，+13.37 pp；Q2 pre-training 能不能彌補 tokenization，答案是 no，tokenization 的效果比 pre-training 大。這兩個問題都有受控實驗支持。

繼續做還能加什麼？

258M 完整訓練：在 NT-v2 框架下大概可以再加 5 pp，到 ~75%，但結論完全不變。Tokenization 還是會是主要瓶頸。

預訓練 13-mer 微生物 GFM：這是值得做的事，但要用到 GTDB 的 40 萬個基因體，需要全新的訓練基礎設施，大概 6 到 12 個月以上。這不是現有 thesis 的延伸，這是一個全新的 project。

競爭的問題也要考慮：這個領域現在進展很快，每個月都有新 paper 出來。我們現在的結果是清楚的，等太久可能會被類似 work 搶先。

---

## Slide 14 — Future Directions: Decision Points

最後這張我想請老師幫我決定幾件事。

方向 A 是現在就開始準備投稿，把現有的結果整理成 paper。目標我覺得 Briefings in Bioinformatics 或 NAR Genomics and Bioinformatics 都很適合，影響因子有 9.5 和 5 左右。Thesis 裡大部分的圖和表都可以直接用，6 月可以完成 draft，8 月投出去。

方向 B 是同時跑 258M 的完整訓練，這個不衝突，可以當 paper revision 的時候加進去。主要需要實作 streaming dataloader，讓訓練不受記憶體限制。

方向 C 是預訓練 13-mer microbial GFM，這個我建議當成下一個 project 來做，而不是現在 thesis 的一部分。

我主要想請教老師的是：以目前的結果，哪個 venue 最合適？以及口試的時程怎麼安排比較好？

---

## Slide 16 (Backup) — Genome Length vs Classification Bias

（如果老師問：scatter plot 上 high-abundance genera 被高估，是不是因為 genome 比較長所以 reads 比較多？）

不是 genome 長度造成的，有兩個原因。

第一，ART 確實是用 coverage-based 模擬，也就是說較長的 genome 產生比較多的 reads。從 read header 裡面的 position 數字和我們統計的 per-genome read 數量可以確認，每個 genome 大概產生 263 到 413 個 reads，中位數 326，這確實跟 genome 長度有關。

第二，但是我們的 balanced subsampling 把這個效應完全消除了。`subsample_balanced.py` 是對每個 species 各取固定數量的 reads，不是對每個 genome 取。所以在我們的訓練集和驗證集裡，每個 species 的 reads 數量是一樣的，真實的 genus abundance 就等於 n_species_in_genus 除以 1535，跟任何 genome 的長度完全無關。

那真正的原因是什麼？是 classification bias。常見的 genus，也就是 species 比較多、訓練資料比較多的 genus，在模型裡的 representation 比較強，logit 比較大，decision boundary 比較寬。當 rare genus 的 reads 被 misclassify 的時候，它們傾向落到常見 genus 的區域裡，而不是均勻分散到所有 genus。結果就是 rare genera 的 predicted abundance 被低估，common genera 的被高估。這是一個系統性的偏差。

量化支撐：我們有 33.9% 的 reads 被 misclassify，這些 reads 不是隨機分散的，而是集中到 logit 比較高的常見 genus，造成 scatter plot 上那個 high-abundance 的點飄到 identity line 上方。

---
