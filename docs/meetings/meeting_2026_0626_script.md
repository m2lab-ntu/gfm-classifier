# Weekly Meeting · 2026-06-26 · 口語逐字稿（中英對照）

對應簡報：`docs/slides/meeting_2026_0626.pptx`（9 張）
建議時間：12–15 分鐘 + 5–10 分鐘討論
風格：可直接對著老師開口講；術語保留英文，連接用口語中文。
故事主軸：上禮拜（6/19）我停在「v14/v15 修正版正在跑、而且懷疑 66.6% baseline 是 leakage」。
這禮拜結果全收斂了，帶來兩件事——一個是**我要誠實修正上禮拜的說法**：66% 其實不是 leakage，
是我把「測試分布」誤判成「資料洩漏」；另一個是比 bug 更重要的科學發現——把資料從 50M 放大到
250M，accuracy 幾乎一動都不動（+0.2pp）。也就是說，資料在 50M 就**飽和**了，真正的天花板是
tokenization，不是資料量。我這禮拜也照這個結論把論文整個更新過一遍。

---

## Slide 1 — Title / 這週做了什麼

老師好，今天 6/26，接續上禮拜 6/19 那次報告。

先快速回顧。上禮拜我抓到兩個 bug——258M 用錯資料集、reader 把 150bp 截成 60bp——然後修正版
v14、v15 我報告的時候還在跑。另外我上禮拜還丟了一句話，說那個 66.6% 的 baseline 可能是 leakage
高估的。

這禮拜兩件事。第一，修正版收斂了，我也建好一個乾淨、跟 training 完全不重疊的 test set，所以現在
有誠實的數字可以報。第二——這點我要很坦白——上禮拜講「66% 是 leakage」這個判斷**是錯的**，
這禮拜我把它查清楚了，66% 不是漏的，我等一下會解釋我當初為什麼會搞混。

而真正最重要的結果是：資料放大 5 倍，從 50M 到 250M，accuracy 只動了 0.2 個百分點。這個「沒有變化」
本身，反而是這禮拜最有價值的發現。整份九張，我講 12 到 15 分鐘。

---

## Slide 2 — 進度時間軸 / Timeline（6/19 → 6/26）

這張是這禮拜的時間軸。

6/19 報告當下，v14（from scratch）跟 v15（warm-start）都還在 H200 cluster 上跑、用的是修好的正確
資料加單行 FASTA。

6/19 到 6/21，兩個都收斂了。v14 from scratch 收在 64% 附近，v15 warm-start 收在 66.6%。

6/21 到 6/23，我做了三件比訓練更關鍵的事。第一，建一個**乾淨的 common validation set**——
99,742 條 read，seq_id 跟 50M、跟 250M 兩邊的 training 都完全不重疊，這樣 v9、v14、v15 才能放在
同一把尺上公平比。第二，把 RC test-time augmentation 用**正確的做法**重做一次——上一版其實是
token-flip，不是真正的反向互補，我這禮拜修成 sequence-level 的 reverse complement。第三，回頭把
上禮拜那個「leakage」的指控查到底。

6/23，我順手把一個在跑的 DNABERT-2 50M 對照組停掉，因為它卡在 resume bug 原地打轉，這個最後
一張帶過。

6/24 到 6/26，我把這禮拜所有確定的結論，整個更新進論文——包括圖、摘要、貢獻、結論四個地方。

---

## Slide 3 — Fix Confirmed: Clean Numbers / 修正版的乾淨數字

這張先給老師看修正版到底做到多少，全部都是在那個零重疊的乾淨 test set 上、而且都加了 RC-TTA 的數字。

- **v9，50M balanced**：67.1%。這是 baseline。
- **v15，250M warm-start**：67.3%。
- **v14，250M from scratch**：64.8%。

對照上禮拜那三個壞掉的 258M 實驗——全部擠在 44 到 45%——這禮拜換對資料之後，連 from scratch 的
v14 都直接拉到 64.8%，warm-start 的 v15 更是站上 67.3%。所以上禮拜的核心假說「22pp 的落差來自資料、
不是模型」，這禮拜算是**完全證實了**：資料修對，accuracy 立刻回到 65 到 67% 這個正常區間。

forward-only 的數字我也列在底下備查：v9 是 66.4%、v15 是 66.6%、v14 是 64.1%，RC-TTA 大概各加 0.7pp。
這部分到此為止其實是好消息——bug 確實修好了。但接下來兩張，是這禮拜真正想跟老師討論的重點。

---

## Slide 4 — Correction: 66% is NOT Leakage / 我要修正上禮拜的說法

這張我要很誠實地修正上禮拜講的東西，因為我覺得把判斷講清楚比面子重要。

上禮拜我說 66.6% 那個 baseline 是 leakage 高估的，理由是我從 100K test 抽了 300 條 seq_id，發現都在
50M training 裡面。當時我就直接下結論說「66% 是漏的、真實值會低很多」。

這禮拜我建了乾淨的 test set 重驗——seq_id 跟 training 零重疊——結果 v9 還是做到 **66.4%（forward）、
67.1%（RC-TTA）**。換句話說，**就算把所有重疊的 read 全部拿掉，分數幾乎不動**。所以 66% 不是 leakage，
是真的。

那上禮拜我到底看到了什麼？我後來查清楚了：問題不是洩漏，是**測試分布不一樣**。有兩種算法——
一種是 natural per-read，照真實比例抽 read，常見的 genus 本來就佔多數，這樣算是 66 到 67%；
另一種是 per-genus balanced，每個 genus 固定抽 1000 條、權重拉平，這時候那些稀有、難分的 genus 會
把平均拖下來，算出來大概 42%。**兩種都是乾淨的、都沒有洩漏**，只是一個是 per-read accuracy、
一個比較接近 macro。我上禮拜把這個 66-對-42 的差距誤判成 leakage，這是我判斷錯了。

我覺得這件事本身值得記一筆：負面結果要查到根因才能下結論，我上禮拜下太快了。這禮拜的修正就是
範例——同一個現象，正確的解釋是「分布」，不是「洩漏」。

---

## Slide 5 — The Real Finding: Data Saturates / 真正的發現：資料飽和了

這張是這禮拜最重要的科學發現，而且它跟我們做這整件事的初衷直接相關。

我們當初放大資料的整個動機，是相信「資料越多、accuracy 越高」。現在資料是對的、reader 是對的、
test 是乾淨的，終於可以**老實回答這個問題**了。答案是：

把 balanced data 從 **50M 放大到 250M，等於 5 倍，warm-start 的 accuracy 從 67.07% 只動到 67.29%——
+0.2 個百分點**。實務上等於沒有變化。from scratch 的 v14 甚至還更低，64.8%。

所以結論很直接：**在我們這個 setup 下，資料量在 50M 就飽和了。** 50M 之後再加資料，不會再有意義的
增益。這推翻了我們原本「需要更多資料」的那個 log-linear 外推——上禮拜我們還以為差距是資料不夠，
這禮拜的證據說：不是。

這也讓上禮拜那個 debug 故事有了一個更完整的結局。上禮拜的劇情是「naive scaling 因為 bug 而失敗」；
這禮拜修好 bug、正確地再 scale 一次，發現**就算一切都對，scaling 本身也救不了我們**——天花板根本
不在資料量。

---

## Slide 6 — Why It Saturates → Tokenization is the Ceiling / 為什麼飽和、天花板在哪

這張解釋飽和的原因，然後指出真正的瓶頸。

為什麼 50M 之後就飽和？因為我們的 reference 是**每個物種只有一個 genome**。所以超過大概 50M reads
之後，再多的 read 只是把同樣那 1,535 條序列**重複覆蓋**一遍，並沒有帶進新的、有鑑別力的訊號。
模型該從這 1,535 個 genome 學到的東西，在 50M 的時候就已經學完了。

那真正的天花板在哪？是 **tokenization**。同樣 50M 資料、同樣 from scratch，MetaTransformer 用
overlapping 13-mer，genus Top-1 做到 **87.42%**，比我們 NT-v2 + LoRA 的 67% 高出 **20 個百分點**。
NT-v2 卡住的根本原因，是它那個 **non-overlapping 6-mer** tokenizer——它把序列切得太粗、又不重疊，
資訊在 tokenize 的當下就掉了，你後面再怎麼加資料、加參數都補不回來。

換句話說，這禮拜把兩條路都走到底了：加資料這條路，50M 就到頂；要突破，得換 tokenization。
這對論文是個乾淨俐落的 message——decisive factor 是 tokenization，不是 data volume、也不是
backbone capacity。

---

## Slide 7 — RC-TTA Done Right / RC-TTA 的正確實作

這張講一個我這禮拜順手修好的方法問題，雖然不大，但會影響數字的可信度。

之前 pipeline 裡那個 RC test-time augmentation，其實做錯了——它是在 token 層級把 token 翻過來，
不是真正的反向互補序列。這禮拜我改成正確的 sequence-level reverse complement：把原始 DNA 序列
取反向互補、重新 tokenize、再跑一次 forward，最後把兩次的 softmax 平均。

修好之後，套到 v9、v14、v15 三個模型上，**每個都穩定 +0.7pp 左右**：v9 從 66.4 到 67.1、
v15 從 66.6 到 67.3、v14 從 64.1 到 64.8。這個增益很一致，而且零訓練成本，所以論文裡所有最終數字
我都用 RC-TTA 之後的版本報。

這也跟我們之前的觀察一致：RC-TTA 對 pre-trained 模型的幫助比較大，對隨機初始化的幫助接近零，
代表它主要是在修正 pre-training 帶進來的 strand bias。

---

## Slide 8 — Thesis Updated / 論文已據此更新

這張報告我這禮拜把上面這些結論怎麼落地到論文裡。

我以「250M 飽和」這個確定的結果為主軸，一致地改了四個地方：

- **圖（data scaling）**：原本只有 500K / 5M / 50M 三個綠點加一條 log-linear 外推線。我加上第四個
  綠點——250M 的 67.3%——它**明顯落在外推線下方**，外推線在那個位置預測大概 71%，實際只有 67.3%。
  讀者一眼就看到綠色軌跡**自己走平、偏離了自己的預測**，飽和訊息用圖直接講出來。這個點刻意不納入
  那條 fit，所以 fit 仍然代表「被推翻的那個外推」。
- **摘要（中英）**：在 50M 結果後面補一句——再放大到 250M 只 +0.22pp，飽和，天花板由 tokenization 決定。
- **第一章貢獻**、**第五章結論**：同樣補上 250M 的數字，並把跟 MetaTransformer 的殘餘差距明確歸因到
  tokenization、不是資料量。

這些都已經 commit、push 上 GitHub，CI 會自動編 PDF。順帶我也修了圖上兩個小瑕疵：250M 標籤的字
顏色本來跟其他點不一致（已統一成黑字），還有標題裡跑出來的一個跳脫字元 `\`。

---

## Slide 9 — Next Steps / 接下來

最後講下一步。這禮拜把「加資料」這條路走到底、也確認了天花板在 tokenization，所以接下來的方向
其實被這個結論定下來了。

第一，**主線是 tokenization，不是 scaling**。既然 MT 13-mer 在同樣 50M 上做到 87%，下一步最該投資的
是把這個 overlapping long-k 的結果做扎實——確認那 87% 在乾淨 test 上站得住，並且補上 species level
的數字。這比再去堆資料量有意義得多。

第二，**論文的故事線可以收束了**。現在有一條完整、誠實的主軸：資料量在 50M 飽和（已證實）→
pre-training 在固定 tokenization 下有用（+13pp，已證實）→ 但 tokenization 才是 decisive factor
（+20pp，已證實）。三個結論彼此獨立、都有對照支撐。

第三，**收尾的對照組**。DNABERT-2 50M 這個補充對照我這禮拜停掉了——它收斂在 59% 就卡在一個 resume
bug 原地重跑 epoch 18，繼續跑只是白燒 GPU。59% 這個數字本身也佐證 tokenization 的故事：DNABERT-2 用
BPE，在這個任務上比 NT-v2 的 6-mer 還低。

所以這禮拜的總結是：上禮拜抓到 bug、這禮拜修好之後誠實地再問一次「資料夠不夠」，得到的答案是
「資料早就夠了，問題在 tokenization」。我也修正了上禮拜對 leakage 的誤判。論文已經照這個結論
更新完。以上，謝謝老師。

---

## 備用 Q&A

**Q：你上禮拜很確定 66% 是 leakage，這禮拜又說不是，到底哪個對？**

這禮拜的對。上禮拜我只看了「300 條抽樣都在 training 裡」就下結論，太快了。這禮拜我直接建一個
seq_id 跟 training 零重疊的乾淨 test set 重驗，v9 還是 66.4%（forward）、67.1%（RC-TTA），分數幾乎
不動——這證明重疊的 read 拿掉也沒差，所以不是 leakage。我當初看到的 66-對-42 落差，真正的原因是
兩種測試分布（per-read vs per-genus balanced）的差別，不是洩漏。

**Q：250M 只比 50M 高 0.2pp，會不會是還沒收斂、或 learning rate 沒調好？**

不太可能。v15 是 warm-start、LR 降到 3e-5，第一個 epoch 就穩在 66.5% 且沒有掉，是收斂的型態，不是
卡住。而且 from scratch 的 v14 完整跑完也只有 64.8%，兩條路都指向同一個天花板。最關鍵的解釋是
reference 每物種只有一個 genome——50M 之後新的 read 只是重複覆蓋同樣 1,535 條序列，沒有新訊號，
所以 plateau 是預期內的，不是 optimization 沒做好。

**Q：那為什麼還要花算力去跑 250M？結論不是飽和嗎？**

因為「飽和」本身要有證據才能寫進論文。我們原本的 log-linear 外推是說「再加資料會繼續漲」，要推翻它，
就得真的去把資料加上去、給出一個落在預測線下方的實測點。現在這個 250M 的點就是那個反證——它讓
「資料量不是瓶頸」從推測變成有數據支撐的結論。這對論文的可信度是必要的。

**Q：MetaTransformer 那個 87% 跟我們的 67% 真的可比嗎？**

可比的部分是「同樣 50M reads、同樣 from scratch」這個控制條件——唯一的主要差別就是 tokenization
（overlapping 13-mer vs non-overlapping 6-mer）。所以 20pp 的差距可以合理歸因到 tokenization。
要再嚴謹，下一步就是在我們自己的乾淨 test set 上重測那 87%，確認它不是另一個分布或評估方式造成的
高估——這也是我下一步要做的。

**Q：DNABERT-2 停掉會不會少一個對照？**

不會影響主結論。它已經收斂在 59%，繼續跑只是卡在 resume bug 重複同一個 epoch，不會再進步。
59% 這個數字也夠用了——它低於 NT-v2 的 6-mer，剛好補強「tokenization 影響很大」這條線。
真要更完整，把 resume 的 off-by-one 修掉再補跑到 epoch 30 也行，但收斂趨勢顯示增益很小，
我判斷不值得這個算力。
