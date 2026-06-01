# Weekly Meeting · 2026-05-31 · 中文逐字稿

對應簡報：`meeting_2026_0531.pptx`（10 張）
建議時間：15–20 分鐘 + 5–10 分鐘討論
語氣：5/28 後的進度回報 + 6 個 decision 中的 3 個今天希望確認

---

## Slide 1 — Title · Updates Since 5/28

老師好。今天的 weekly 主要是接續 5/28 那次 meeting 之後的進度。

那次我們列了 6 個 decision points，今天的 deck 主要做三件事：

1. 報告兩天內完成了什麼
2. 一個沒預期到的新發現（這個我蠻意外的）
3. 6 個 decision 的 status，今天希望老師幫我確認其中 3 個

整個 deck 10 張，預計 15-20 分鐘。

---

## Slide 2 — Progress Timeline · 5/28 → 5/30

兩天內三件事完成：

**第一**, Taiwana-2 那邊把 MT 6 個 predictions 重跑了，把 read 順序對齊到 TWCC 的 reads_100K.fa，這樣 in-DB fair-comparison 才能正確套 mask。**6 個裡面 5 個成功**，MT 13-mer hier 那個 checkpoint 損壞了——Taiwana-2 那邊 model 在 batch 10000、val_loss=9.29 就停了沒訓練完，所以那個無法產出。

**第二**，in-DB fair-comparison Table 4.30 寫進 thesis，species 跟 genus 兩個 panel 都完整。

**第三**，是這個 deck 主要要報告的——意外發現 **genus level 在 fair-restricted 設定下，MT 13-mer 反超 Kraken2 +17 pp**。原本以為只有 species level 有 Kraken2 主導的故事，現在發現 genus 端反過來了。

底下紅字：**TWCC 額度 5/30 見底**——iService wallet 顯示 -802.521 點，sbatch 拒絕新 job。這是個 blocker，等下會專門講。

---

## Slide 3 — MT Alignment Fix

這張說明 MT 預測順序問題怎麼修的，以及修完之後數字怎麼變。

左邊 panel · Species level：MT 13-mer flat 從 49.7% 升到 53.7%（+4 pp）。MT 6-mer 兩個變化很小（9.0% vs 9.2%, 6.4% vs 6.4%）。**為什麼 13-mer 那個變化大**——原本的數字是在 MT 自己 val_dir 的 100K subset（多檔 FASTA、檔名排序），新數字是在 TWCC 的 reads_100K.fa 單檔順序上跑。兩個 100K 不是同一批 reads，所以模型表現會差。

右邊 panel · Genus level：MT 13-mer genus 從 87.4% 升到 94.25%。這個差距更大但其實 condition 也更不同——舊的 87.4% 是 5M val pool + 50K reads/sample，新的 94.25% 是 100K test + 1K reads/sample。不同 evaluation condition 的數字。**重點不在數字升降，而在新數字才是跟 thesis 其他所有模型在同一個 evaluation 條件下的**。

底下灰底 box 解釋了 root cause：MT 原本 parse_fasta_dir 讀多個 .fa 串接，順序跟 reads_100K.fa 單檔不一致——驗證方法是用 NT-v2 labels 對位比對 MT labels，每個 MT class 平均對應到 64 個不同 NT class。修完後 1:1 完美對齊。

下面綠色 takeaway：**所有 MT in-DB 指標現在都正確算在 canonical 100K test set 上**。

---

## Slide 4 — Species/Genus Performance Inversion（新發現）

這是這個 deck 最重要的一張。in-DB fair-restricted 設定下：

**左 panel · Species level (1535 classes)**：Kraken2 主導
- Kraken2: 77.18% read acc / Pearson r 0.847
- MT 13-mer flat: 52.64% / 0.514
- NT-v2 per-genus oracle: 27.69% / 0.156
- NT-Species flat: 17.12% / 0.142
- Kraken2 領先 MT 13-mer **+24 pp read acc**, **+0.33 Pearson r**

**右 panel · Genus level (120 classes)**：MT 13-mer 反超
- **MT 13-mer genus: 94.89% / r 0.9993** ← 最高（不計 oracle trivial 100%）
- NT-v2 oracle: 100% (trivial，用真實 genus label)
- Kraken2: 77.68% / 0.823
- NT-Genus v9: 68.88% / 0.992
- MT 13-mer 領先 Kraken2 **+17 pp read acc**, **+0.18 Pearson r**

**這個 inversion 完全沒預料到**。原本以為 Kraken2 在所有 task 都會主導，因為它的 k-mer matching 對 simulated reads 結構性有利。但 genus level MT 13-mer 反而贏。

下面橙色 takeaway：**同 DB、同 test set、同 protocol——Kraken2 贏 species，MT 13-mer 贏 genus**。

---

## Slide 5 — Why the Inversion · Commit-Rate × Cardinality

機制解釋。為什麼會 inversion？

**左 box · Species level (1535 classes)**：
- Kraken2 commit 70% reads，剩 30% unclassified
- 1535 species 分散 30% 的「lost signal」，每個 species 平均才損失 ~0.2 reads
- Kraken2 commit 那 70% 上 99.33% 正確——**精度極高，分散損失可承受**
- → high precision on commits 贏，分散的 30% loss 可接受

**右 box · Genus level (120 classes)**：
- Kraken2 還是 commit 70%
- 但 120 genera 分散 30% lost signal，每個 genus 損失 ~2.5 reads——**集中**
- MT 13-mer 對所有 reads 都給 prediction，整體 ~95% accuracy
- → MT 13-mer 的 full coverage 贏，30% 的 loss 現在是 ~30% 的訊號損失

底下橙色 box：**這個發現補強 thesis 的 complementary positioning**——不是「neural 通用 / Kraken2 限定」的簡單二分，而是 **precision-vs-recall tradeoff 隨 task cardinality 翻轉**。Paper discussion 可以多寫一段 commit-rate analysis。

---

## Slide 6 — Thesis Updates Summary

兩欄表格。

**左欄 · What changed**：
- Table 4.29 MT 那幾行換成 aligned 版本
- MT 13-mer hier 那行標 N/A（checkpoint 損壞）
- Hierarchical-masking paragraph 改寫：移除已壞 hier 數字、保留兩個 router 對比（NT-Genus 66%, MT 6-mer 49%）+ 引用 read-level Section 4.spv4 的三點 monotonic 證據（包括 MT 13-mer router 87.5% 那點仍然有 read-level data）
- **OOD framing 修正**——這是個重要修正。之前寫「neural retains signal on OOD」其實是錯的 framing，那 219 GCF species 對 neural 是 in-distribution，因為 balanced_50M 訓練資料就包含這 1535 species。正確 framing 是 **deployment coverage asymmetry**：Kraken2 需要 reference FASTA 才能建 DB，neural 不需要

**右欄 · What was added**：
- 新增 Table 4.30：fair-restricted comparison（species + genus panels）
- 新增三段討論：
  - 「Coverage-restricted fair comparison」解釋為什麼 restrict 到 85,819 reads
  - 「Sharp inversion between species and genus levels」解釋新發現
  - 「Kraken2 dependence on database coverage」修正 OOD framing

頁數：137 → 139 頁。

---

## Slide 7 — Blocker · TWCC Budget Exhausted

5/30 下午 sbatch 出來這個 warning：「You do not have enough credits in your iService wallet -802.521」。**現在 TWCC 完全無法提交新 job**。

三欄分析：

**綠色 · Still possible (no GPU)**：
- thesis 文字校稿、figure 重生（matplotlib）
- 接收 Taiwana-2 送來的 .npz 跑 evaluate_sample.py（CPU）

**紅色 · Blocked (needs budget)**：
- DNABERT-2 50M resubmit (~36 hr)
- Speed/memory benchmark (3 hr, 還要先把 MT 模型搬到 H100)
- HMP real-dataset inference (3 hr)
- 任何未來 GPU 工作

**金色 · Decision needed**：
- 跟老師確認加值 → 我可以繼續 P0 工作
- 或者接受 DNABERT-2 17/30 partial 結果，這部分結束
- Taiwana-2 那邊可以做 MT 13-mer hier 重訓
- 或全部 defer 到 6/15 口試前再處理

下面紅色 takeaway：**需要 decision——加值還是接受 partial + defer**？

---

## Slide 8 — 6 Decision Points Recap

5/28 我列了 6 個 decision points，目前 status：

- **Q1: DNABERT-2 resubmit** → 我建議做（36 hr 換完整 backbone scaling table，CP 高）。卡 TWCC 預算。
- **Q2: DNABERT-1 取消** → 我建議取消（剩 13 天 wall clock，5M 數據+成本論證已足）
- **Q3: MT 13-mer hier 重訓 (Taiwana-2)** → 看老師意願（thesis 已標 N/A，read-level 三點 monotonic 仍有效）
- **Q4: Speed benchmark** → 必做（老師要求）。卡 TWCC 預算+MT 搬遷。
- **Q5: 258M training** → 我建議不做（log-fit +4.2 pp 不影響結論）
- **Q6: HMP real-dataset 驗證** → 6 月做（thesis nice-to-have，paper must-have）

綠色 = 建議做，紅色 = 建議不做/取消，橙色 = 看老師意願。

Q2、Q5、Q6 我已經有明確建議。Q1、Q3、Q4 今天希望老師確認。

---

## Slide 9 — Recommended Priorities (next 2 weeks)

按算力需求分三層。

**綠色 · Immediate (不需 TWCC GPU)**：
- 接收 Taiwana-2 的 Per-genus 13-mer (Exp F) 結果 → 補進 thesis Table 4.hier-prelim
- MT 13-mer hier 重訓 (Q3 decision)
- 重生 figures（用新 aligned MT 數字）
- Thesis 校稿 + format 一致性檢查

這些都不用 TWCC 算力，可以立刻做。

**金色 · 需要 TWCC 加值 (~45 GPU-hr)**：
- DNABERT-2 50M resubmit (36 hr) — 完整 backbone scaling table
- Speed/memory unified benchmark (3 hr) — must-do
- HMP mock community real-dataset inference (3 hr) — paper submission

加總 45 GPU-hr，預算負擔很溫和——如果老師願意加值。

**紅色 · 建議不做 (need explicit decision if 老師要做)**：
- DNABERT-1 50M 繼續：300 GPU-hr / 13 天，CP 太低
- 258M 完整訓練：290 GPU-hr / 18 天，跨不過 tokenization gap

---

## Slide 10 — Asks for Today's Meeting

今天希望老師具體回答三個 decision：

**Q1 · TWCC 預算**：要加值嗎？加值的話我可以 resubmit DNABERT-2（36 hr）+ 跑 speed benchmark（3 hr）。或都 defer？

**Q2 · DNABERT-1 50M**：確認取消嗎？如果取消，5M 數據 + per-epoch cost 11.7 hr vs NT-v2 2.8 hr 的對比，就用來論證「DNABERT-1 訓練成本本身就是 limitation」。

**Q3 · MT 13-mer hier 重訓 (Taiwana-2)**：值得花 1-2 天 V100 補 thesis Table 4.30 那一行嗎？或接受 N/A（read-level Section 4.spv4 三點 monotonic 故事仍完整）？

---

## 給自己的 backup Q&A（口頭備援）

### Q: 為什麼 MT 13-mer genus 94.89% 比之前 87.4% 高那麼多？
A: 之前 87.4% 是在 5M val pool（stratified split）+ 50K reads/sample 上算的。新 94.25% 是在 100K independent test set + 1K reads/sample 上算的。Test set 不同 + sample size 不同。重點不是「升了 7 pp」，而是「現在跟其他所有模型在同樣 100K test 上比較才有意義」。

### Q: Kraken2 在 species 領先這麼多 (+24 pp)，paper 是不是要強調 neural 不如 k-mer？
A: 完全相反。Paper 強調的是 **complementary**——同 DB 同 reads 條件下 Kraken2 species 領先，但 (a) genus level inversion 顯示這個領先 task-dependent (b) Kraken2 需要 reference FASTA，新發現物種無法處理 (c) 我們的 fair-restricted 比較本身就證明對話可以這樣展開——不是 paper 弱化，是 paper 把 conversation framing 講清楚。

### Q: 為什麼 OOD framing 之前寫錯，現在才發現？
A: 一開始我把「Kraken2 對 219 GCF species accuracy=0%」框成「OOD test」，但其實這 219 species 是 balanced_50M 訓練資料的一部分，對 neural 是 in-distribution。正確 framing 是「deployment coverage asymmetry」——Kraken2 需要 reference FASTA 才能放進 DB，neural 不需要。前一版 thesis 段落會誤導 reader，所以這次修正。

### Q: Taiwana-2 預算還夠嗎？
A: 老師之前剛加值，目前 Per-genus 13-mer 在跑（60/81 genera 完成），剩下的應該夠。如果要加做 MT 13-mer hier 重訓，再評估。

### Q: 6/15 口試準備如何？
A: Thesis 主體 139 頁完整，main contribution 都有實驗支撐。剩下都是補強，不是 critical path。如果今天 Q1-Q3 確認後，6/1-6/10 可以 focus 在 thesis 校稿、figure regen、defense slides。

---

## Slide-to-Time 對照

| Slide | 內容 | 時間 |
|---|---|---|
| 1 | Title + recap | 1 min |
| 2 | Progress timeline | 1.5 min |
| 3 | MT alignment fix | 2 min |
| 4 | Species/Genus inversion 新發現 | 3 min |
| 5 | Why inversion mechanism | 2 min |
| 6 | Thesis updates summary | 2 min |
| 7 | TWCC budget blocker | 2 min |
| 8 | 6 decision points recap | 1.5 min |
| 9 | Recommended priorities | 1.5 min |
| 10 | Asks Q1-Q3 | 1.5 min |
| **Total** | | **~18 min** |

留 7-12 分鐘給老師討論 Q1-Q3。
