# Weekly Meeting · 2026-06-19 · 中文逐字稿

對應簡報：`docs/slides/meeting_2026_0619.pptx`（8 張）
建議時間：12–15 分鐘 + 5–10 分鐘討論
故事主軸：上週 (6/9) benchmark 跑完、v9 50M 已經有 66.6%，這週的計畫是把 genus
分類器從 50M 擴到 258M、期待靠 5× 資料量再加 2–5 pp。結果不但沒漲、反而掉到 ~44.5%。
這週的核心工作是把這個「資料越多反而越差」的反直覺現象**診斷清楚**，並啟動修正方案
（250M balanced subset，v14）。

---

## Slide 1 — Title

老師好。今天是 6/19，對應上週 6/9 那次進度之後的一週。

上週結束時，NT-v2 genus 分類器在 50M 平衡資料上已經做到 66.6%（這是 v9）。
這週原本的計畫很單純：把訓練資料從 50M 擴大到完整的 258M，期待靠 5 倍的資料量
再往上推 2 到 5 個百分點。

結果完全相反——擴到 258M 之後，準確率不升反降，掉到大約 44.5%，少了 22 個百分點。
這週最重要的工作，就是把這個反直覺的現象徹底診斷清楚，找到真正的瓶頸，
然後啟動正確的修正方案。

這個 deck 8 張，大概 12 到 15 分鐘。

---

## Slide 2 — 進度時間軸

這張時間軸從上週 6/9 一直到今天。

6/11，我把 v10 丟出去：258M 完整資料、從 v9 的 best checkpoint 做 warm-start、
而且因為資料不平衡，我「想當然耳」地開了 class_weights=true。

6/13 拿到結果，整個 collapse：100K 獨立測試集只有 40.1%，比 v9 的 66.6% 還低很多。
訓練過程中 val_acc 從頭到尾卡在 21% 完全不動。

6/14 是這週的轉折點——我把 collapse 的原因定位出來了，是 class_weights 在
400:1 的不平衡下把 loss 扭曲掉了。確認原因之後，我同時丟了兩個對照組：
v12（warm-start）跟 v13（從零開始），兩個都把 class_weights 關掉。

6/15 到 6/18，兩個實驗都收斂在 ~44.5%，warm-start 跟 from-scratch 幾乎沒差。
這個結果反而幫我確認了真正的瓶頸是「資料」，不是初始化。於是我啟動了
250M 的**平衡**子集抽樣，要拿來訓練 v14。今天那個抽樣 job 還在跑第二階段。

---

## Slide 3 — The Scaling Paradox

這張把「期待」跟「現實」並排。

左邊是當初的期待。深度學習的常識是資料越多越好——v9 用 50M 平衡資料做到 66.6%，
我預期擴到 258M（5 倍）應該可以再加 2 到 5 pp，樂觀一點摸到 70% 左右。

右邊是實際發生的事。所有 258M 的實驗都掉下來了：
v10（開 class_weights）100K 測試只有 40.1%，
v12（warm-start、關 weights）45.4%，
v13（從零、關 weights）44.5%。

三個 258M 的點全部落在 40–45% 這一帶，相對 v9 是往下掉 22 個百分點。
這就是這週要解釋的核心矛盾：**資料量變 5 倍，準確率反而砍掉三分之一。**

---

## Slide 4 — v10 Collapse → Root Cause

先看 v10 為什麼 collapse。

左圖是 v10 的 val_acc 曲線。它從 epoch 1 到 epoch 12 完全卡在 21% 上下動不了，
最後 early stopping。綠色虛線是 v9 的 66.6% baseline，橘色虛線是 v10 在 100K 測試集的
40.1%——注意這兩個數字的差距，整整 26 pp。

右邊是診斷結果，我在 6/14 確認的。

第一，問題出在 `class_weights=true`。我用 inverse genus frequency 去加權 loss，
上限設 10 倍。

第二，258M 的 genus 不平衡大約是 400:1。這裡要解釋一下：258M 其實是
**species-balanced**（每個物種讀數差不多），但是不同的 genus 底下含的物種數量差很多，
所以聚合到 genus level 的時候就變成 400:1 的高度不平衡。

第三，把這兩件事乘起來：稀有 genus 被乘上 10 倍的權重，主導了整個 gradient，
模型被迫去追尾巴的稀有類別，結果在數量最多的 head genus 上 collapse。
這就是為什麼 val_acc 卡在 21%。

第四，最關鍵的反證——v9。v9 的 50M 資料其實也有 349:1 的不平衡，但它**沒有**
加權，照樣做到 66.6%。所以 class_weights 是 v10 collapse 的唯一元兇，
不是資料量、也不是 warm-start。

---

## Slide 5 — Four Experiments, One Conclusion

這張把四個實驗的完整設定跟結果列在一起。

- **v9**：50M 平衡資料、從零訓練、不加權、30 epochs → 66.6%。這是 baseline。
- **v10**：258M、warm-start、**加權**、跑到 epoch 12 early stop → 40.1%，collapse。
- **v12**：258M、warm-start、**不加權**、只跑到 3 epochs → 45.4%。
- **v13**：258M、從零、**不加權**、完整 25 epochs → 44.5%。

兩個註記：
v10 是在 epoch 12 因為 val_acc 不動而 early stop（原本排 15）。
v12 只跑到 3 epochs 是因為它分配到的節點 NFS 是冷的，一個 epoch 要 476 分鐘，
撞到 23 小時的 wall time——這個之後 slide 7 會講。

最重要的結論在底下黃框：三個 258M 的實驗，不管 warm-start 還是 from-scratch、
不管跑幾個 epoch，全部收斂在 44 到 45%，遠低於 v9 平衡資料的 66.6%。
**warm-start 跟從零訓練沒有差別，代表天花板是被「資料」決定的，不是被初始化決定的。**

---

## Slide 6 — Key Finding: Balance > Volume

這張是這週最重要的 takeaway。

左圖三根 bar：v9 的 50M 平衡 66.6%、v13 的 258M 不平衡 44.5%、
還有右邊斜線那根是 v14 的 250M 平衡——那是目標，現在還在跑。

右邊四個結論：

第一，**資料量不是瓶頸**。5 倍的 reads 沒有幫助，warm-start 跟 scratch 都卡在 44.5%。

第二，**不平衡才是瓶頸**。400:1 的 genus 偏斜讓數量多的 head genus 主導學習，
尾巴的 genus 永遠學不好。

第三，**加權是個陷阱**。直接用 inverse-frequency 加權（v10）會 collapse；
把它拿掉（v12/v13）也只能回到 45%——因為不平衡的本質還在，加權只是換一種壞法。

第四，**真正的解法是平衡資料本身**。與其在 loss 上動手腳，不如直接複製 v9 的
平衡配方，但把規模拉到 250M。這就是 v14。

一句話總結：在這個任務上，決定天花板的是 class balance，不是 read 數量。

---

## Slide 7 — Infrastructure Lessons (64-GPU DDP)

這張是這週在 64-GPU DDP 上學到的工程教訓，對之後的大規模訓練很重要。

左圖是這週最戲劇性的數字：同樣一個 epoch，分配到 NFS cache 是冷的節點（v12）
要 476 分鐘；分配到 cache 是熱的節點（v13）只要 43 分鐘——差了 11 倍。
差別純粹來自於 job 落在哪一組節點、那組節點有沒有把 47 GB 的 FASTA index
快取起來。

右邊是 DDP 的設定與瓶頸：
- 規模是 8 個節點 × 8 張 H200 = 64 GPU。
- batch 是每卡 128，乘上 64 = 有效 batch 8192。
- 真正的瓶頸是 lazy FASTA index 走 NFS——258M reads、47 GB。
- 冷熱差 476 vs 43 分鐘。
- account quota 也要喬：兩個 job 都要 64 GPU 會撞到 MaxGRESPerAccount，
  所以 v12 用 MST114414、v13 用 MST114550 分流。
- 23 小時的 soft wall limit，靠 last.pt 自動 resume 接力。

底下綠框的教訓：大型 DDP run 之前，要先把 FASTA index 預熱或 pin 住，
不然冷 cache 的 run 等於用 10 倍的 GPU-hours 跑同一個 epoch，非常浪費。

---

## Slide 8 — Next Steps · v14 = 250M Balanced

最後是接下來的計畫。

**正在跑的**：
250M 的平衡子集抽樣（subsample_balanced.py，job 118820），現在在跑第二階段的
reservoir sampling。規格是 1535 個物種、每個物種 162,866 reads（min 145K、max 184K），
湊出一個平衡的 250M 資料集。

**這週要做的**：
- v14 訓練：用跟 v9 完全一樣的 pipeline（class_weights=false），在這個平衡 250M 上
  跑 64-GPU DDP。
- 補做 v13 的 100K 測試集評估——目前 v13 只有 val 的數字，還沒在獨立測試集上跑過。

**預期結果**：
假設成立的話，平衡的 250M 應該要 ≥ v9 的 66.6%，這樣就能正面確認
「資料平衡」才是真正的 lever。如果確認，我們在論文裡就有一個乾淨的 scaling story：
**先平衡，再放大**——而不是丟更多原始資料進去。

以上，這週主要是把一個反直覺的負面結果診斷清楚，並把修正方案啟動了。謝謝老師。

---

## 備用 Q&A

**Q：為什麼一開始要開 class_weights？**

因為 258M 在 genus level 有 400:1 的不平衡，直覺上加權是處理不平衡的標準做法。
但 v9 的反證說明，在這個任務上 backbone 本身夠強，輕度到中度的不平衡不需要加權；
強行加權反而會讓稀有類別的 gradient 蓋過主體，造成 collapse。

**Q：v12 為什麼只跑了 3 個 epoch，數字還能拿來比嗎？**

v12 卡在冷 NFS（476 分鐘/epoch），撞 wall time 只跑到 epoch 3。
但它在 3 個 epoch 已經收斂到 45.4% 且 warm-start 從 66.3% 一路掉到 45%，
趨勢非常明確；加上 v13 完整 25 epochs 也是 44.5%，兩者互相佐證，結論是穩的。

**Q：258M 跟 50M 都是 species-balanced，為什麼結果差這麼多？**

這正是我請 Nano5 那邊一起追的問題。目前可確認的是：
genus-level 的不平衡程度是主要嫌疑（v9/v10/v12/v13 的對照已經把 class_weights
這個變因排除）。v14 的平衡 250M 就是直接的驗證實驗——如果它回到 66%，
就坐實了是資料組成的問題。

**Q：v14 如果還是回不到 66.6% 怎麼辦？**

那代表瓶頸不只是 genus balance，可能還有 train/test 分布差異或 species 組成的
問題，下一步會比對 v9 跟 258M 兩個資料集的 genome 來源與 read 生成方式。
但目前所有證據都指向 balance，v14 是最直接、最高 CP 值的驗證。

**Q：這個負面結果對論文有沒有價值？**

有，而且是好材料。「naive scaling + naive re-weighting 都會失敗，必須先平衡再放大」
本身就是一個乾淨、可重現的 ablation story，比單純報一個高分更有說服力。
