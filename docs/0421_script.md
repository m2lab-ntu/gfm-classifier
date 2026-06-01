# 0421 進度報告逐字稿

---

## Slide 1 — Title

大家好，這週的進度主要有三個部分：第一是台灣杉二號那邊的 MetaTransformer 實驗有了新的、更完整的結果；第二是 TWCC 的訓練 job 有加值繼續跑；第三是 hierarchical evaluation 的程式碼已經準備好了。

---

## Slide 2 — MetaTransformer Extended Ablation（section）

先講 MetaTransformer 的完整實驗結果。

---

## Slide 3 — Full Tokenization Ablation（Genus）

上週我報告了 6-mer 和 12-mer 的結果，這週額外跑了 13-mer 的設定，然後所有結果加在一起整理成這張完整表格。

一共六種設定：k 等於 6、12、13，stride 等於 1 或等於 k。

最高的是 MetaTransformer 13-mer overlapping，87.42%。這是從頭訓練的、沒有任何 pre-training，但已經超過 NT-v2+LoRA 加 RC TTA 的 67.07%（v9 收斂結果），差了 20.35 個百分點。

13-mer non-overlapping 只有 27.30%，幾乎是最差的。這再次確認 stride 的影響比 k 的選擇更關鍵——13-mer 如果用 non-overlapping，每條 read 只有 11 個 token，大部分序列資訊都不見了。

Overlapping 三個設定的排名是：6-mer 48.87% < 12-mer 78.83% < 13-mer 87.42%，單調遞增，k 越大越好。

---

## Slide 4 — Full Tokenization Ablation（Species）

同樣的六種設定，這次看 species-level 的結果，1535 個 class。

13-mer overlapping 達到 49.62%，而且這是沒有任何 hierarchical routing 的 flat classifier。相比之下，我們的 NT-v2 based sp_v4 目前在 17.31%，還沒收斂。

12-mer non-overlapping 和 13-mer non-overlapping 分別只有 0.64% 和 0.51%，幾乎等於亂猜——1535 個 class 的 random baseline 大約是 0.065%，所以雖然比 random 好一點點，但幾乎沒有意義。這說明 token 數太少的時候，species-level 的細粒度辨識完全沒辦法做。

---

## Slide 5 — Key Finding

這週最重要的結論是：tokenization 對效能的影響遠超 pre-training。

具體的數字是這樣：fixed tokenization 看 pre-training 的效果是 +18.29pp；fixed architecture 看 tokenization 的效果，從 6-mer 到 13-mer，是 +40pp 以上，而且沒有用到任何 pre-training。

最終結果：MT 13-mer stride=1 以 87.42% 超越 NT-v2+LoRA（67.07% RC TTA）20.35pp。一個從頭訓練的小模型，只要 tokenization 對了，就可以遠超一個用大量基因體資料預訓練的 foundation model。

這也讓 future work 的方向更明確：如果有一個用 overlapping 13-mer 訓練的 GFM，把 tokenization 的優勢跟 pre-training 的 representation quality 結合起來，理論上應該可以遠超 87.42%。

---

## Slide 6 — Ongoing Training（section）

接著說一下 TWCC 那邊的訓練進度。

---

## Slide 7 — v9 & sp_v4 Training Progress

加值之後 TWCC 的兩個 job 都恢復了。

v9 genus 目前跑到 ep30，best val acc 66.29%，每個 epoch 還在穩定進步，沒有觸發 early stopping，代表還沒收斂。48 小時的 SLURM 時限到了之後已經重新提交繼續跑。

sp_v4 species 目前跑到 ep26，best val acc 17.31%，斜率也還很陡，同樣繼續跑。

右邊的 learning curve 圖可以看到兩個模型都有中間的 LR restart dip——那是之前 SLURM job 沒有正確 resume cosine schedule 造成的，ep17（v9）和 ep13（sp_v4）之後已經修好了。兩條曲線現在都是穩定上升。

---

## Slide 8 — Code & Thesis Updates（section）

最後說一下程式碼和論文的部分。

---

## Slide 9 — Hierarchical Eval Code Ready

Hierarchical evaluation 的程式碼已經寫進 evaluate.py，一個指令可以同時跑四種模式：

第一個是 flat，就是 sp_v4 直接輸出；第二個是 oracle，用 true genus label 來 mask species logits，這是理論上限；第三個是 hard top-K，用 genus model 預測 top-K genus 來做 hard mask；第四個是 soft routing，就是 Pr(genus) × P(species|genus) 的機率乘積。

本地端的 100K subset test 已經跑完了，preliminary results 在下一張。

---

## Slide 10 — Preliminary Hierarchical Eval（100K Subset）

這張是 100K 筆資料的初步結果，用 v9 ep30 的 genus model 和 sp_v4 ep26 的 species model。

Genus model 在這個 subset 上的準確率是 65.7%，也就是說大概有 34% 的 read genus 預測是錯的。

四種模式的 Top-1：Flat baseline 是 16.4%；Hard Top-5 routing 是 16.5%，只差 0.1 個百分點；Soft routing 是 16.2%，比 baseline 還低一點點；Oracle 是 27.9%，比 baseline 高了 11.5 個百分點。

Hard routing 和 soft routing 幾乎沒有提升的原因是：genus 錯誤率 34% 引入的 noise，把正確 routing 帶來的增益幾乎全部抵消掉了。這是數學上可以預期的——genus 準確率要到大約 80% 以上，routing 才會有明顯效果。

Oracle 的 +11.5 pp 代表的是：如果 genus 是完美的，species 最多可以再進步多少。這個數字確認了方向是對的——genus 是瓶頸。

Long-tail 的問題：flat baseline 下有 804 個 species F1=0；oracle 下也還有 632 個，因為這些 species 訓練樣本太少，光靠 routing 是沒辦法解決的。

---

## Slide 11 — Thesis Updates

論文這週也同步更新了。

Chapter 4 的 tokenization ablation section 擴充為六種設定，新增了兩個表格，一個是 genus-level，一個是 species-level。analysis 段落加了「MT 13-mer 超越 NT-v2+LoRA」這個核心發現，以及 stride 和 k-mer 長度的複合效果分析。

另外 sp_v4 的 interim results 更新到 ep26、17.31%，然後新增了一個 subsection 放 hierarchical evaluation 的 preliminary results，包含四種模式的表格和三段 analysis：genus bottleneck、oracle gap、long-tail 問題。

Chapter 5 的 contribution 更新為包含 13-mer 的完整結論，future work 加了「k=13 是否是 optimum」和「13-mer pre-trained GFM」的方向，concluding remarks 也更新為以 87.42% 作為 key result。

Learning curve 圖也更新到 ep30（v9）和 ep26（sp_v4）。

---

## Slide 12 — Next Steps

接下來的工作。

v9 和 sp_v4 繼續跑到收斂，SLURM 時限到了之後重新提交。

v9 收斂之後跑 RC TTA eval 拿到最終數字，更新論文的 tab:v8-results 和相關段落。

兩個都收斂之後跑 full hierarchical evaluation，用 5M 筆測試資料，比較四種模式的結果，這個結果預計會是論文最後一個實驗。

論文的部分等這些數字出來再補最終結果進去。

---
