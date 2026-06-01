# 0407 Weekly Progress — 逐字稿

---

## Slide 1 — Title

好，換我了。這週除了訓練進度之外，因為上週老師說可以開始準備論文了，所以我也整理了一下文獻回顧的部分，今天一起報告。

---

## Slide 2 — Thesis Overview（section）

先從論文背景開始。

---

## Slide 3 — Research Background

大家應該對這個研究方向已經有基本的了解，我就快速帶過一下。

我的論文是用 genomic foundation model 做 metagenomics 的 taxonomic classification。Input 是 150 bp 的 short reads，task 是把每條 read 分到 genus（120 個 class）或 species（1535 個 class）。

Dataset 是用 HGR-UMGS 的 2505 個基因組，ART 模擬 Illumina 定序，產生 258M 條 reads，我 subsample 了 50M 條做 balanced 訓練。

Baseline 是 MetaTransformer（Wichmann et al. 2023），genus recall 98.3%，是目前 SOTA。他們用 HGR-UMGS 完整資料集（2,505 物種，coverage factor 4）訓練，300K steps × batch 2,048。注意這個 training throughput 的量綱跟我們的 dataset size 不一樣，不能直接比。

---

## Slide 4 — Related Work: Classification Methods

我把這個領域的方法分成四類，整理進論文的文獻回顧。

最早是 alignment-based，BLAST 跟 DIAMOND，準確但慢，實務上沒辦法處理百萬量級的 reads。

現在業界最常用的是 k-mer / hash-based，Kraken2 跟 Centrifuge。速度快，但完全綁定 reference database，沒有泛化能力。

深度學習方面，DeepMicrobes（2020）是第一個比較完整的 DL 方案，LSTM 加 attention。MetaTransformer（2023）是現在的 SOTA，自己設計的 5M 參數 Transformer，12-mer tokenization。

我的方法是第四類，用 pre-trained GFM 加 LoRA fine-tuning。核心 claim 是：backbone 已經從大量基因組中學到通用 DNA 表示，所以在資料量遠少於 MetaTransformer 的情況下也能達到不錯的效果。

---

## Slide 5 — Related Work: Genomic Foundation Models

GFM 這邊，論文裡我主要討論這四個模型的比較。

DNABERT（2021）是最早把 BERT 用到 DNA 的，6-mer tokenization，12 層，但只在人類基因組上 pre-train。

我用的是 Nucleotide Transformer v2，Dalla-Torre et al. 2024，發在 Nature Methods。在 3202 個基因組、850 個物種上 pre-train，multi-species，ESM-2 架構，29 層，498M 參數。

DNABERT-2 用 BPE tokenization，117M 參數，比較輕量，也是 multi-species。

Evo 是最新的，最大 7B 參數，single-nucleotide，可以做生成，但計算成本比較高。

我選 NT-v2 的理由主要是：multi-species pre-training 最接近 metagenomics 的情境，6-mer 剛好讓 150 bp fit 進 32 個 token，H100 上 batch 256 跑得動，HuggingFace 有 public weights。這部分我在論文 ch3 有寫一個專門的小節說明 model selection rationale。

---

## Slide 6 — Our Approach

方法的部分大家應該聽過不少次了，我就快速帶過。

NT-v2 當 backbone，LoRA rank 16 作用在 Q/K/V，只有 5.54M 參數是 trainable，是整個 498M 的 1.11%。Head 是 4-head attention pooling，aggregate 32 個 token 的表示再接 classifier。

訓練分兩個 phase：先 freeze backbone 只 train head，再把 LoRA 跟 head 一起 joint train，用 differential lr，backbone 比 head 低一個量級。

RC TTA 就是 inference 的時候同時跑 forward 跟 reverse complement，logits 加起來再 argmax，免費多 0.1 到 1.5 個 pp。

---

## Slide 7 — Key Finding: Data Scaling

這是目前最核心的發現，我在論文 ch4 有完整的 scaling analysis。

500K 上跑過很多 ablation，logit adjustment、RC consistency loss、換 head 架構，每個 trick 頂多 ±0.5 pp。

但 data 從 500K 擴到 5M，accuracy 直接跳 7.76 pp；5M 到 50M 再加 3.01 pp。

結論：data volume 遠比任何 training trick 重要。這個圖是 log-linear scaling，邊際效益遞減，要追上 MetaTransformer 的 98.3% 需要的 data 遠超過 50M。

---

## Slide 8 — Hardware Constraints

這邊說明一下為什麼只能在 TWCC 的 H100 上跑，而不能用台灣杉二號或我自己的 RTX 4090。

我的 training setup 是 NT-v2 498M 參數，BF16，batch 256，有開 gradient checkpointing。Dataset 是 50M 條 reads，FASTA 加上 label TSV 大概 12.7 GB，存在 TWCC 的 /work NFS 上。

台灣杉二號的問題有兩個：第一，V100 是 Volta 架構，CC 7.0，不支援 BF16 硬體加速，只能跑 FP32。FP32 activation memory 大概是 BF16 的兩倍，batch 256 下就算是 32 GB V100 也會 OOM。第二，Taiwania-2 沒有 mount TWCC 的 /work，資料根本拿不到。

RTX 4090 是 Ada 架構，BF16 沒問題，但 VRAM 只有 24 GB，batch 256 跑 NT-v2 會很緊，大概要降到 64 以下，每個 epoch 的 update 數少很多，收斂變慢。更根本的問題是 /work 在 TWCC cluster 內部，本地機器直接連不過去，12.7 GB 的資料搬過來也不是長久之計。

H100 是 80 GB，batch 256 加 gradient checkpointing 有充裕的 margin，/work 直接 mount，BF16 tensor throughput 大概是 4090 的三倍。所以只能在這裡跑。

---

## Slide 9 — Training Results（section）

接下來是這週的訓練進度。

---

## Slide 10 — v9 Genus Classifier

v9 現在跑到 epoch 22，forward val accuracy 65.68%，learning curve 還在上升。

之前 epoch 10 有做過完整的 evaluation，RC TTA 是 66.06%，比 v8 的 63.05% 多了 3.01 pp。

Learning curve 上 epoch 7 跟 11 有兩個 dip，是 SLURM job timeout 之後 resume 的時候 LR scheduler 被重置造成的。這個 bug 已經修掉了，epoch 17 之後 scheduler 正確地接著 cosine decay，沒有再出現 dip。

目前暫停，因為 iService credit 用完了，需要加值才能繼續 submit job。

---

## Slide 11 — sp_v4 Species Classifier

sp_v4 是 species 分類，1535 個 class，epoch 18，val accuracy 16.37%，也還在上升。

Random baseline 0.065%，所以 16% 是有學到東西的。Species 比 genus 難很多，同 genus 不同 species 的基因組差異很小。

同樣在 epoch 7 有 LR restart 的 dip，epoch 13 之後 fix 好了。現在也是 paused 狀態。

---

## Slide 12 — Bug Fix（section）

簡單說一下這週 fix 的 bug。

---

## Slide 13 — Resume Logic Bug Fix

Bug 在 EarlyStopping 的 resume 邏輯。舊的 checkpoint 裡 `best_val_acc` 這個 key 存在但 value 是 None。原本的 guard 只有 `if 'best_val_acc' in ckpt`，check 過了就把 `early_stop.best` 設成 None，導致 resume 後第一個 epoch 一定被標成 best。

Fix 是一行：`best_val = ckpt.get('best_val_acc') or ckpt.get('val_acc')`，如果是 None 就 fallback 到 actual val_acc。

LR restart 的問題是另一個 root cause：舊的 checkpoint 沒存 scheduler state，resume 之後 scheduler 從頭 warm up。現在 last.pt 一定會存 optimizer 跟 scheduler 的 state dict，這個問題也解了。

---

## Slide 14 — Next Steps

加值之後重新 submit v9 extend 跟 sp_v4 resume。

v9 大概還有 8 個 epoch 會收斂，收斂後跑完整的 RC TTA evaluation 拿到最終數字。

sp_v4 收斂後跑 top-k genus routing evaluation，然後實作 hierarchical classification pipeline。

論文的部分，ch4 這週已經更新到最新的 interim results，等兩個 model 收斂後補 final numbers。

以上。
