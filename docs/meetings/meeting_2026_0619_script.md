# Weekly Meeting · 2026-06-19 · 中文逐字稿

對應簡報：`docs/slides/meeting_2026_0619.pptx`（8 張）
建議時間：12–15 分鐘 + 5–10 分鐘討論
故事主軸：上週 (6/9) benchmark 跑完、v9 50M 已經有 66.6%，這週的計畫是把 genus
分類器從 50M 擴到 258M、期待靠 5× 資料量再加 2–5 pp。結果不但沒漲、反而掉到 ~44.5%。
一開始以為是 class_weights 的問題，但關掉之後 (v12/v13) 還是只有 45%。
這週的核心工作是把這個「資料越多反而越差」的反直覺現象**診斷清楚**——透過 code+data
audit，發現真正的元兇是一個 FASTA 讀取的 bug：258M 的 reads 在訓練時被截斷成 60bp
（150bp 只讀到第一行），加上 66.6% 這個 baseline 其實有 test/train 洩漏被高估。
結論不是「資料不平衡」，修正方案是先修 reader、重建乾淨 test set，再重測 volume/balance。

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

6/14 我先猜是 class_weights 在 400:1 的不平衡下把 loss 扭曲掉了。為了驗證，我同時丟了
兩個對照組：v12（warm-start）跟 v13（從零開始），兩個都把 class_weights 關掉。

6/15 到 6/18，兩個實驗都收斂在 ~44.5%，warm-start 跟 from-scratch 幾乎沒差，
class_weights 關掉也沒救回來。這說明瓶頸既不是初始化、也不是加權。於是我回頭做 code 跟
data 的 audit，找到真正的元兇：258M 的訓練是走 train_ddp.py 的 lazy loader，
那個 `_read_seq` 只讀每筆 record 的第一行；偏偏 258M 的 FASTA 是 60 欄 wrap 的，
所以每條 150bp 的 read 只被讀進前 60bp——模型實際只看到 40% 的序列。
v9 走的是另一條路徑（train.py 的 `_parse_fasta`，會把多行接起來），讀到完整 150bp。
另外我也發現 66.6% 這個 baseline 有問題：100K test 的 read 100% 落在 50M 訓練集裡，
是洩漏高估的。今天的工作就是把 reader 修好、重建乾淨 test set，再重測。

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

先看 v10 為什麼 collapse，然後講我後來查到的真正原因。

左圖是 v10 的 val_acc 曲線。它從 epoch 1 到 epoch 12 完全卡在 21% 上下動不了，
最後 early stopping。綠色虛線是 v9 的 66.6% baseline，橘色虛線是 v10 在 100K 測試集的
40.1%。一開始我以為這是 class_weights 把 loss 扭曲掉的結果。

但 v12/v13 把 class_weights 關掉之後還是只有 45%，所以我做了 code+data audit，
右邊是真正的診斷，我在 6/18 確認的，跟 class_weights 沒關係。

第一，也是最關鍵：**258M 的 reads 在訓練時被截斷成 60bp**。258M 的訓練走的是
train_ddp.py 的 lazy loader，裡面的 `_read_seq` 只讀每筆 record 的第一行；
而 258M 的 FASTA 是 60 欄 wrap 的（150bp 拆成 60+60+30 三行），所以模型每條 read
只讀到前 60bp，等於丟掉 60% 的序列。這點我直接在源檔上跑過那段邏輯驗證，回傳就是 60。

第二，v9 之所以正常，是因為它走**另一條、正確的**路徑——train.py 的 `_parse_fasta`
會把多行接起來，讀到完整 150bp，而且 v9 的檔案本身是單行的。同一個模型、同一份
基因組，差別只在讀檔的程式碼。

第三，66.6% 這個 baseline 本身也被高估了：100K 測試集的 seq_id 我抽查 300 筆，
**300 筆全部都在 50M 訓練資料裡**——這不是乾淨的 holdout，是洩漏。

第四，所以「genus 不平衡」不是原因。v9 是 349:1、v13 是 400:1，幾乎一樣，
卻差了 22 個百分點，不平衡解釋不了。class_weights 只是讓 v10 額外更糟而已
（40% vs 45%），不是這 22pp 的主因。

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
不管加不加權、不管跑幾個 epoch，全部收斂在 44 到 45%。
**這種「什麼變因都動不了天花板」的型態，指向一個三者共用的「輸入」問題，
而不是初始化或加權。**這就是為什麼我去 audit 讀檔流程，最後找到那個
把 150bp 截成 60bp 的 reader bug。

---

## Slide 6 — Key Finding: Balance > Volume

這張是這週最重要的 takeaway，而且結論跟我原本以為的不一樣。

左圖是真正的根因：模型實際看到的 read 長度。v9 走 train.py 的 `_parse_fasta`，
看到完整 150bp；v10/v12/v13 走 train_ddp.py 的 `_read_seq`，在 wrap 的 258M 檔上
只看到 60bp。少了 60% 的輸入——這才是那 22pp 的來源。

右邊四個結論：

第一，**這是個讀檔的 bug，不是 scaling 的極限**。`_read_seq` 只讀一行，
偏偏 258M 的檔是 60 欄 wrap 的，所以每條 read 被截成 60bp。

第二，**兩條程式路徑分岔了**。v9 的 reader 會把多行接起來、讀到完整 read；
DDP 那條不會。同一份資料、同一個模型，差別只在讀檔的 code。

第三，**66.6% 的 baseline 是漏的**。100K test 完全落在 50M 訓練集裡（100% 重疊），
所以 v9 這個數字被高估，真正乾淨的 baseline 我們其實還不知道、而且會更低。

第四，**volume 跟 balance 其實都還沒被真正測過**。沒有任何一個 258M 的 run
看到完整的 read，所以在 reader 修好之前，我們不能對「資料量」或「平衡」下任何結論。

一句話總結：這週最大的收穫不是一個分數，而是抓到一個會讓所有 258M 實驗失真的
pipeline bug——在修好它之前，先別急著解讀 scaling。

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

最後是接下來的計畫。重點是：在修好 reader 之前，所有 258M 的數字都不能採信，
所以順序很重要。

**第一步——修掉真正的 bug**：
- 修 `_read_seq`：讓它讀到下一個 `>` 為止，把 wrap 的多行接起來（大概 5 行的改動），
  並在訓練啟動時印出樣本長度，確認是 150bp 才往下跑。
- 重建一個**乾淨的 100K test set**：seq_id 與訓練資料完全不重疊，然後用它把 v9
  重新評估一次，得到一個誠實的 baseline（會比 66.6% 低）。

**第二步——用完整 150bp 重跑**：
- 258M full-length：把 reader 修好之後重訓 258M（class_weights=false），
  這才是第一次真正在測「資料量」。
- v14 250M 平衡子集（subsample_balanced.py，job 118820，1535 species × 約 163K reads，
  輸出是單行）當作「平衡」這個變因的對照組。

**第三步——這時候才能下結論**：
- volume：修好之後的 258M，能不能贏過乾淨的 v9 baseline？
- balance：v14 對比 full-read 258M，才能把「平衡」單獨隔離出來。

所以這週最重要的不是一個新分數，而是抓到一個會讓所有 258M 實驗失真的 reader bug。
這對論文反而是好材料：一個「naive scaling 因為一個 pipeline bug 而失敗、找到並修正」
的除錯故事，比直接報一個高分更扎實。謝謝老師。

---

## 備用 Q&A

**Q：為什麼一開始要開 class_weights？**

因為 258M 在 genus level 有 400:1 的不平衡，直覺上加權是處理不平衡的標準做法，
所以 v10 我就開了。但這其實是個誤判：關掉之後 (v12/v13) 一樣只有 45%，
代表加權不是主因。事後 audit 才發現真正的問題在讀檔（reads 被截成 60bp），
跟加權、跟不平衡都無關。class_weights 只是讓 v10 在那個基礎上額外更糟而已。

**Q：v12 為什麼只跑了 3 個 epoch，數字還能拿來比嗎？**

v12 卡在冷 NFS（476 分鐘/epoch），撞 wall time 只跑到 epoch 3。
但它在 3 個 epoch 已經收斂到 45.4% 且 warm-start 從 66.3% 一路掉到 45%，
趨勢非常明確；加上 v13 完整 25 epochs 也是 44.5%，兩者互相佐證，結論是穩的。

**Q：258M 跟 50M 都是 species-balanced，為什麼結果差這麼多？**

答案不是資料組成，而是讀檔路徑不同。50M（v9）走 train.py 的 `_parse_fasta`，
會把 FASTA 的多行序列接起來，讀到完整 150bp；而且 50M 的檔是單行的。
258M（v10/v12/v13）走 train_ddp.py 的 lazy loader，`_read_seq` 只讀第一行，
偏偏 258M 的檔是 60 欄 wrap，所以每條 read 只讀到 60bp。我直接在源檔上重跑那段
邏輯確認過，回傳就是 60。所以差別不在「資料」，在「同一份資料被兩個不同的 reader
讀成不同長度」。另外 66.6% 本身也有 test/train 洩漏，是高估的。

**Q：reader 修好之後，如果 258M 還是回不到 baseline 怎麼辦？**

先講清楚：要比的是「乾淨的 v9 baseline」，不是被洩漏高估的 66.6%。
如果修好 reader、用完整 150bp 重跑之後，258M 仍然贏不過乾淨 baseline，
那才輪到下一層假設——genus balance、train/test 分布差異、或 genome 來源不同。
那時候 v14 的平衡 250M 就是隔離「平衡」這個變因的對照組。但這些都要等 reader
修好、有乾淨 test set 之後才有意義，否則只是在錯的數字上繞圈。

**Q：這個負面結果對論文有沒有價值？**

有，而且是好材料——但價值在於除錯的嚴謹，不在「平衡」這個結論（那還沒被證實）。
故事是：5× 資料看似讓準確率崩了，透過系統性對照（warm/scratch、加減 weights、
不同 epoch 都收斂在同一個天花板）排除了初始化與加權，最後用 code+data audit
定位到一個讓所有大規模實驗失真的 reader bug，並修正。這種「反直覺結果 →
有紀律地排除假設 → 找到真因」的過程，比直接報一個高分更能展現研究的可信度。
