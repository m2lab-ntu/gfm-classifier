# 0427 進度報告逐字稿

---

## Slide 1 — Title

老師好，這週的進度比較多，我先把幾個重點列出來：第一，TWCC 上的所有訓練 job 這週都收斂了，包含 v9 genus、sp_v4 species、DNABERT、DNABERT-2；第二，tokenization ablation 這邊新增了 DNABERT 系列的比較結果；第三，我做了一個 sample-level 的 application evaluation，把 67% 的 per-read accuracy 轉換成比較有實際意義的 abundance estimation 和 binary detection 指標；第四，per-genus 50M 的 LoRA training 已經在本地跑起來了；最後，我這週也和 co-advisor 有一次討論，她的評估想跟老師報告一下。

---

## Slide 2 — This Week's Highlights

就是這五個重點。第三個 sample-level evaluation 是這週最主要的新結果，結論是 67% 的 per-read accuracy 在 sample level 轉換成 Pearson r = 0.993 的 abundance 估計，以及在 abundance ≥ 1% 的 genus 上有 100% 的 detection sensitivity。

---

## Slide 3 — Section: Completed Experiments Overview

先來總覽一下目前所有跑完的實驗。

---

## Slide 4 — All Completed Experiments

這張是目前所有完成實驗的整理。

Genus classification 部分：v8（5M）63.05%、v9（50M）67.07% RC TTA，v9 這週在 ep30 收斂。Species 部分：sp_v4（50M）17.55% forward Top-1，同樣在 ep30 收斂。

MetaTransformer tokenization ablation 這邊六種設定都跑完了，最高是 13-mer stride=1 的 87.42%。

Backbone 比較：NT-v2 63.05%、DNABERT 61.78%、DNABERT-2 58.88%，這是這週新增的數字。

Hierarchical 的部分是在 100K subset 上的 preliminary result，predicted routing 11.2%、oracle 21.8%。

最底下是 sample-level evaluation，這是這週完全新增的，稍後詳細說。

---

## Slide 5 — Section: Tokenization Ablation — New Results

先說 DNABERT 和 DNABERT-2 的比較結果。

---

## Slide 6 — Pre-trained GFM Backbone Comparison (5M)

這張是在同樣的 5M balanced data 下，三種不同 pre-trained backbone 的比較。設定都一樣：LoRA r=16、attention-pooling head、30 epochs、RC TTA。

NT-v2 的 63.05% 比 DNABERT 的 61.78% 高了 1.27 個百分點，比 DNABERT-2 的 58.88% 高了 4.17 個百分點。

DNABERT 雖然用 overlapping 6-mer（145 個 token），資訊量比 NT-v2 的非重疊 25 個 token 豐富，但 NT-v2 還是贏了——主要是 backbone 規模（499M vs 86M）和 pre-training data 多樣性的優勢。

DNABERT-2 速度最快，7,259 reads/s，比 NT-v2（2,584）快了將近 3 倍——但同時也是準確率最低的。短 BPE token 減少了計算量，但可能把 taxonomically informative 的 motif 切碎了。

有一個方法論上的問題需要說明：三個模型的 batch size 不同（NT-v2: 32、DNABERT: 128、DNABERT-2: 256），是因為序列長度不同、GPU memory 限制。這造成 gradient steps 不等——NT-v2 有 453K 次更新，DNABERT 只有 117K，DNABERT-2 更少，只有 59K。我們的比較是 epoch-based，也就是每個模型都看過訓練資料 30 次，這是 fine-tuning 比較的標準做法。即使 step 數不等，排名不太可能翻轉——DNABERT 在 4 倍更少更新的情況下只落後 NT-v2 1.27 個百分點，而 DNABERT-2 的差距主要來自 BPE tokenization 本身。

這個結果的結論是：在 5M data scale 下，pre-training 的 quality 比 tokenization strategy 更重要。

---

## Slide 7 — Full Tokenization + Backbone Comparison

這張把所有實驗放在一起從高到低排。

最高是 MT 13-mer stride=1（50M，從頭訓練）87.42%，然後 MT 12-mer stride=1（50M）78.83%，接下來是 NT-v2+LoRA v9（50M）67.07%。

這裡有一個有趣的 flip：在 5M 的 data scale，NT-v2 pre-training 贏了 DNABERT overlapping 6-mer；但在 50M 的 data scale，MT 13-mer overlapping 從頭訓練就遠超了 NT-v2+LoRA。所以 pre-training 的優勢是相對的——tokenization 在 data 夠多的時候會蓋過 pre-training。

最下面四個 non-overlapping 設定全部都很差，27.30% 以下，這再次確認 stride=1 是必要條件。

NT-v2 的根本限制是這行：6-mer tokenization 是 pre-training 時固定的，fine-tune 的時候沒辦法改。所以 NT-v2 的天花板在 67%，不是因為 backbone 不夠大，是因為 tokenization 鎖死了。

---

## Slide 8 — Section: Sample-Level Application Evaluation

接下來說 sample-level evaluation，這是這週最主要的新結果。

---

## Slide 9 — Motivation: Per-read Accuracy ≠ Application Utility

    為什麼要做 sample-level evaluation？

    Per-read accuracy 是最嚴苛的評估方式——每一條 read 都要單獨正確分類才算數。但在實際的 metagenomic pipeline 裡，classifier 不是一條一條 read 個別輸出結果，而是對整個 sample 的幾萬條 read 做 aggregate。

    這週和 co-advisor 討論的時候，她建議可以做這個分析來補充說明 67% 的 per-read accuracy 在 application 層面代表什麼，以回應老師對 accuracy 不夠高的疑慮。

    實驗設定直接用既有的 5M validation predictions，不需要重新訓練：100 個 random-partition samples，每個 50K reads，評估 relative abundance estimation；另外 200 個 sparse-community samples，每個 50K reads、60 個 genus 在裡面，評估 binary detection。Ground truth 100% 已知，因為是 ART simulation。

---

## Slide 10 — Abundance Scatter Plot

先說這張圖是怎麼生出來的。

**資料來源**是 v9 evaluation 時存下來的 `predictions_rc_tta.npz`——裡面有 5M 筆 validation reads 的 predicted label 和 true label，不需要重跑任何模型。

**Sample 的建構方式**：把這 5M 筆 reads 隨機打亂，切成 100 個不重疊的 sample，每個 50K reads。注意這是直接在 val set 上切，每個 sample 裡 120 個 genus 都有 reads，比例約等於 balanced 抽樣的比例（每個 genus 約 1/120，也就是 417 reads/genus/sample）。

**每個點的計算**：對每一個 sample、每一個 genus g，算兩個數字——true abundance = 這 50K 筆裡 true label = g 的比例，predicted abundance = model 預測為 g 的比例。100 samples × 120 genera = 12,000 個點，每個點是一個（sample, genus）pair。

**Pearson r = 0.993** 是跨這 12,000 個點算的。**Bray-Curtis dissimilarity** 是每個 sample 把所有 genus 的 |true - pred| 加總再除以 (true + pred) 的總和，對 100 個 sample 取平均，結果是 0.094。低於 0.1 在 ecology 文獻裡通常被認為是 excellent agreement。

**直覺**：雖然有 33% 的 read 被分錯 genus，但錯誤大致是對稱的——分錯進去 genus A 的 read 數，和從 genus A 分錯出去的 read 數接近，aggregate 之後兩邊的誤差互相抵消，所以 abundance 估計仍然很準。這就是 per-read accuracy 低、但 sample-level abundance 還是 r = 0.993 的原因。

---

## Slide 11 — Sensitivity by Abundance

這張是 detection sensitivity 對 true relative abundance 的折線圖。橫軸是 genus 的真實 abundance，縱軸是被偵測到的比率。Detection threshold 是「至少一條 predicted read 屬於這個 genus」。

可以看到在 abundance ≥ 1% 以上，sensitivity 是 100%。在 0.1%–1% 這個區間，sensitivity 還有 97.6%。只有在 0.01%–0.1% 這個非常低 abundance 的區間，sensitivity 才開始下降到 93.9%。

這個結果說明：dominant taxa 在 sample 中是非常容易偵測到的，幾乎不會 miss。

---

## Slide 12 — Binary Detection ROC — Fixed Ground Truth, Swept Threshold

老師上週指出之前的 detection table 有方法論問題：同一個 threshold 同時改變「什麼叫 truly present」和「什麼叫 detected」，sensitivity 和 specificity 都在動，沒有可比性。

這張是修正後的 ROC 分析。做法是：ground truth 固定為 sparse-community 建構時的 present\_set / absent\_set，也就是一個 genus 到底有沒有被放進這個 sample 是完全已知的 binary label；detection threshold 從 0 掃到最高，連續計算 sensitivity 和 specificity，畫出 ROC 曲線。

結果：AUC = 0.705。在 specificity = 95% 的時候，sensitivity 只有 17.2%；specificity = 90% 的時候，sensitivity 30.9%；specificity = 80% 的時候，sensitivity 46.2%。

這個數字比 abundance estimation 差很多，原因是一個根本性的 noise floor 問題：33% 的 per-read misclassification rate，在每個 50K-read sample 裡，對一個 truly absent genus 平均會有 50K × 33% / 120 ≈ 138 個 predicted reads，也就是 0.28% 的 predicted abundance。這個 noise 是 absent genus 的背景值——要達到 95% specificity，detection threshold 必須設在 1.49% 以上，但這樣很多真正 low-abundance 的 genus 就偵測不到了。

所以 binary detection（presence/absence）這個任務在目前 67% accuracy 的模型下確實有根本限制。這跟 Slide 10/11 的 abundance estimation 是不同的性質：abundance estimation 可以靠 error 抵消達到高 Pearson r，但 binary detection 需要能區分 0 和「有一點點」，而 misclassification noise 把這個界線模糊掉了。

這個分析是誠實的：abundance estimation 非常好，但 binary detection 有限制，是這個模型在 application 層面一個清楚的弱點，值得在論文 limitation 章節討論。

---

## Slide 13 — Sample-Level Comparison: NT-v2 LoRA v9 vs MetaTransformer

老師上週要求把 Slide 10/11 的分析也在 MetaTransformer 上跑一遍，這張是結果。

除了 87.43% 的 13-mer，我也跑了 48.82% 的 6-mer stride=1 作為低 accuracy 的對照。

Abundance estimation 這邊：NT-v2 v9 的 Pearson r = 0.993，MT 6-mer 下降到 0.984，MT 13-mer 提升到 0.999。Bray-Curtis 的差距更明顯：NT-v2 0.094、MT 6-mer 0.167（變差）、MT 13-mer 0.028（非常好）。

Detection sensitivity 這邊：NT-v2 在 ≥1% 是 100%，0.1–1% 是 97.6%；MT 13-mer 兩個都是 100%；MT 6-mer 在 ≥1% 還有 99.9%，但 0.1–1% 掉到 86.8%。

最有趣的是 ROC AUC 的差距：NT-v2 0.705 vs MT 13-mer 0.900。這說明 87% 的 per-read accuracy 不只讓 abundance estimation 稍微好一點，而是讓 binary detection 有質變——noise floor 從 0.28% 壓到接近 0.09%，presence/absence 的區分變得可靠很多。

結論：accuracy 的差距在 binary detection 這個任務上放大了，13-mer 的 tokenization 優勢在 sample-level 比 read-level 更明顯。

---

## Slide 14 — Section: Hierarchical Classification

接下來報告 hierarchical classification 這邊的分析。

---

## Slide 15 — Why Routing Barely Helps — and Why Per-genus Is the Right Architecture

之前報告過，Top-5 genus routing 的提升只有 +0.1 pp，幾乎沒有幫助，但 oracle routing 有 +11.5 pp。這週我分析了為什麼。

Root cause 是：sp_v4 的錯誤大部分是 within-genus confusions——同一個 genus 裡面的不同 species 分錯了。這種錯誤靠 masking 不同 genus 的 species 是沒辦法修正的，因為問題根本就在 within-genus 的部分。加上 10% 的 read genus 不在 top-5 裡，這些 read 的 accuracy 直接歸零，把 routing 帶來的增益全部抵消掉。

真正該做的架構是 per-genus classifier：每個 genus 訓練一個獨立的 species 分類器，這個分類器只需要分辨這個 genus 裡面的 species，天然就在解決 within-genus confusion 的問題。

天花板分析：如果 within-genus accuracy 可以到 40%，那 pipeline accuracy = 65.7% × 40% = 26.3%，超過 flat sp_v4 的 16.4%。目前 5M frozen 只有 65.7% × 17% = 11.2%，是因為 data 少、backbone frozen 訓練不夠。50M LoRA 應該可以大幅提升 within-genus accuracy。

---

## Slide 16 — Per-genus 50M LoRA — Training in Progress (33/81)

Per-genus 的訓練現在已經跑到 33/81 個 genus 完成，用 RTX 4090 雙 worker 並行跑，預計再約 44 小時全部完成。

從已完成的結果可以看到一個很清楚的規律：**species 數量越少，accuracy 越高**。Pelosinus（2 species）93.5%、Anaerotruncus（4 species）82.8%、少於 10 個 species 的 genus 平均可以到 55% 以上。相對的，Bacteroides 有 79 個 species，目前只有 15.7%，是目前最困難的 genus。

這個規律是合理的——species 數越多、每個 species 的訓練樣本就越少、類別間的區分也越難。Bacteroides 79 個 species 的問題本質上跟整個 species-level task 類似，但好處是 at least 我們是在 within-genus context 裡訓練的。

另外，所有模型跑到 10 epochs 都還在進步，沒有觸發 early stopping。所以等全部 81 個 genus 跑完之後，我會針對 accuracy 比較低的 genus（比如 Bacteroides、Alistipes）延長訓練到 20–30 epochs，再跑 evaluate_per_genus.py 做整合評估。

---

## Slide 17 — Section: Next Steps — Discussion

接下來是我想跟老師討論的方向選擇。

---

## Slide 18 — Three Directions

基於目前的進度，我歸納了三個可能的方向，想讓老師幫忙決定接下來怎麼走。

Option A 是「現在就收尾提交」。所有主要實驗都完成了，論文也差不多了，per-genus 50M 可以列在 future work 裡面不做。但缺點是 hierarchical pipeline 的 claim 沒有用足夠的 data 完整驗證，有點說不清楚。

Option B 是「等 per-genus 50M 跑完再提交」，這是我自己偏好的方向。Training 現在已經在跑了，再等 2–3 天就有結果。結果出來就可以 end-to-end 展示整個 two-stage pipeline，讓論文的 species-level contribution 比較完整。時間成本很低——就是等一下。

Option C 是「把 genus accuracy 推到 67% 以上再提交」。NT-v2 的 6-mer tokenization 是根本瓶頸，要突破需要 streaming loader 跑 258M 完整資料，或者換一個新的 GFM，至少需要 2–3 個月。這基本上是另一個 research direction 了。

我認為 B 最合適，但想聽老師的意見。

---

## Slide 19 — Thesis Status

最後報告一下論文的狀態。

目前 107 頁，NTU template。Chapter 2 和 3 完整，Chapter 4 實驗章節差不多了：§4.12 tokenization ablation 這週更新了 DNABERT 的比較；§4.14 sample-level evaluation 是這週新增的；只剩 §4.15 per-genus 50M 的結果還沒有，等 2–3 天 training 完成之後補上。Chapter 5 conclusion 也已經更新，abstract 也更新了。

如果老師選 Option B，那就是等 per-genus 50M 出結果、補進論文、最後通讀校稿、提交。時間上應該可以在本週內或下週初完成。

以上，這週的進度報告到這裡，請老師指教。

---
