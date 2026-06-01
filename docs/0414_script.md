# 0414 進度報告逐字稿

---

## Slide 1 — Title

大家好，這週我的進度主要是做了一個 controlled ablation experiment，用來拆解我們的方法跟 MetaTransformer 之間差距的來源，然後結果出來之後有去更新論文。

---

## Slide 2 — MetaTransformer Controlled Ablation（section）

先講這個實驗。

---

## Slide 3 — Motivation

大家知道我們的 v9 是 66%，MetaTransformer 原論文是 98.3%，差了大概 32 個百分點。

問題是這兩個方法同時有三個差異：一個是我們有 pre-training、他們沒有；一個是架構深度不同，我們是 29 層、他們是 1 層；還有一個是 tokenization，我們是 6-mer、他們是 12-mer。

這三個東西同時不一樣，沒辦法說差距是從哪裡來的。

所以這週做的事情是：把 MetaTransformer 的 code 直接拿來，用我們同一份 50M balanced 資料集跑，測了四種不同的 tokenization 設定。這樣可以控制資料量，然後分別把 pre-training 的效果和 tokenization 的效果拆開來看。

實驗是在 Taiwania-2 上跑的，因為 MetaTransformer 只有 5M 參數，不需要 BF16，用 V100 就可以跑。

---

## Slide 4 — Tokenization Explained

在講結果之前先說明一下 tokenization 的設定。

k-mer tokenizer 是用一個長度 k 的視窗在 DNA 序列上滑動，每次往右移動 stride s 個 nucleotide。

Stride 等於 k 的話就是 non-overlapping，每個 nucleotide 只屬於一個 token。150 bp 除以 6 就是 25 個 token，這是 NT-v2 的設定。

Stride 等於 1 的話是 overlapping，每個位置都開一個新的 k-mer。150 bp 用 12-mer 的話是 150 減 12 加 1，就是 139 個 token。

右下角這個表格列出了四種設定的 token 數。可以看到 non-overlapping 12-mer 只有 12 個 token，overlapping 12-mer 有 139 個，差了十幾倍。這個 token 數的差異後面結果會看到非常重要。

---

## Slide 5 — Results

結果在這裡。

五個設定都用同一份資料、同一個 val split 評估。

最高的是 MetaTransformer 12-mer overlapping，78.83%。這個是確定的最終結果，我後來有跑第二個 epoch 來確認有沒有繼續進步，結果是第二個 epoch 立刻嚴重 overfit：train loss 從 0.76 暴跌到 0.12，但 val loss 反而從 1.20 惡化到 2.29。所以 78.83% 就是這個架構的 capacity ceiling，不是 lower bound。

我們的 NT-v2 + LoRA 是 65.29%，forward only。

然後 MetaTransformer 6-mer 兩種設定都在 47-49%，差不多。

從這些數字可以拆出兩個效果：

第一個是 pre-training 的效果。固定 tokenization 都是 6-mer 的情況下，NT-v2 65% 比 MetaTransformer 47% 高了 18.3 個百分點，這就是 pre-training 帶來的優勢。

第二個是 tokenization 的效果。固定用 MetaTransformer 架構，從 6-mer 換成 12-mer overlapping，47% 跳到 78.83%，差了 31.8 個百分點。

---

## Slide 6 — Key Finding

所以這週最重要的發現有兩個。

第一個是：tokenization 的影響比 pre-training 更大。Pre-training 有幫助，+18 pp；12-mer overlapping tokenization 的幫助更大，+31.8 pp。

第二個是：78.83% 是這個架構的 capacity ceiling，不是 lower bound。Epoch 2 的實驗告訴我們，50M 筆資料已經足夠讓這個 5M 參數的 single-encoder model 在一個 epoch 內學到它能學的所有東西，繼續跑只會記住 training data，沒有辦法泛化得更好。

為什麼 12-mer overlapping 有這麼大的效果有兩個原因。第一個是 12-mer 本身比較有辨識力，更長的序列片段在不同的 genus 之間比較不一樣，比 6-mer 更 taxonomically specific。第二個是 overlapping 確保每條 read 有 139 個 token，如果用 non-overlapping 只有 12 個，大部分的序列資訊都被丟掉了。

所以結論是 NT-v2 的根本限制在於它的 6-mer tokenization，這個是 pre-training 的時候就決定了，沒辦法在 fine-tuning 的時候換掉。

理想的方向是有一個用 12-mer overlapping 訓練的 GFM，而且 model size 也要夠大，這樣才能把 12-mer 的辨識力跟 pre-training 的 representation quality 結合起來。

---

## Slide 7 — Thesis Updates（section）

然後這週也同步更新了論文。

---

## Slide 8 — Thesis Updates

Chapter 3 的 Methodology 裡面加了 stride 和 overlap 的定義，還有四種設定的 token 數表格。

Chapter 4 新增了一個 section 專門放這次的 ablation 結果，包含兩段分析分別講 pre-training 和 tokenization 的效果，還有對 NT-v2 限制的討論。另外 MetaTransformer comparison 那個 section 的結論也更新了，不再說差距主要來自資料量，而是指向這兩個 ablation。data scaling 的表格也加上了 v9 那一欄。

Chapter 5 的 contribution 加了一條「tokenization 是最主要的 cross-architecture design factor」，future work 從原本的「tokenization study 待做」改成「12-mer pre-trained GFM」這個具體方向，concluding remarks 也根據新的發現重新寫了。

還有一個小 fix 是目錄裡面誌謝那一行一直沒有出現，這週把它修好了。

---

## Slide 9 — Next Steps

接下來的工作分兩個部分。

Taiwania-2 那邊這週已經跑完了。MetaTransformer 12-mer 的結果確認是 78.83%，論文也同步更新了 capacity ceiling 的分析。

TWCC 這邊等加值之後恢復 v9 和 sp_v4 的訓練，然後跑 hierarchical evaluation，就是用 v9 做 top-k genus routing，看對 species 分類有沒有幫助。

論文的部分等 v9 跟 sp_v4 的最終數字出來再補進去。

---
