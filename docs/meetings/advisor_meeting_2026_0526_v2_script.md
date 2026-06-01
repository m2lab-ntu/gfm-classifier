# 0526 Advisor Meeting · 中文逐字稿（v2 · 視覺化版本）

對應簡報：`advisor_meeting_2026_0526_v2.pptx`（16 張，blank canvas，每張都有對應圖示）
建議時間：32–38 分鐘，留 10 分鐘給老師討論
語氣：彙報 + 詢問意見；數字唸關鍵的就好，圖會幫忙

---

## Slide 1 — Title

老師好。今天我想跟兩位老師一起回顧整個碩士論文的成果，然後針對「畢業之後要不要投稿、要往哪個方向投」討論看看。

簡報分四個部分：第一是研究問題的設定、第二是六個主要 finding、第三是把這些 finding 整合成一個故事、第四是投稿選項——這部分我會列幾個具體的問題請老師指教。

整個 deck 16 張，預計講 32 分鐘，中間有任何想打斷的隨時可以。

---

## Slide 2 — The Problem

先快速 frame 一下任務。

圖上看到的是一個非常單純的 pipeline：input 是一條 150 bp 的 DNA 短讀段，output 是它應該屬於 1535 個物種中的哪一個。中間就是 model——我比較了三種 model 家族：NT-v2、MetaTransformer、跟 Kraken2。

下面三個 challenges 是這個任務為什麼難：
- 150 bp 太短，物種之間共享很多 sub-sequence
- 1535 個 class，每個誤判都污染整個 sample 的豐度估計
- 真實 metagenome 常含 novel organisms，reference DB 沒見過

底下灰底 box 是「為什麼這件事重要」：sample-level 物種豐度是 microbiome、疾病診斷、生態研究的基礎；現有工具像 Kraken2/Bracken 對 novel organisms 處理不好，這就是 learned representation 的研究動機。

---

## Slide 3 — Three Model Families

三個 model 家族並排展示，每個 box 標了它對應的「研究軸」：

- **NT-v2 + LoRA**（綠）：預訓練的 foundation model，498M 參數，6-mer tokenization。LoRA 只訓 1.1%。**這是 pre-training 軸**——拿來看 pre-trained backbone 有沒有幫助。
- **MetaTransformer**（藍）：從頭訓練、5M 參數、沒有 pre-training。它的價值在於可以變動 tokenization：6-mer 跟 NT-v2 對齊，或 13-mer overlapping。**這是 tokenization 軸**——拿來看 tokenizer 選擇的影響。
- **Kraken2**（金）：k=35 exact match，custom DB 用同樣 2505 個基因組建。**這是 algorithm 軸**——拿來看 learned 對比 non-learned 方法。

中間藍底強調：三個軸（tokenization × pre-training × routing）orthogonal，且全部在**同一個 50M 訓練資料、同一個 100K 測試集**上，所以差異不能歸給 data，只能歸給 model design。

底下灰字補充 evaluation：read-level Top-1 加上五個 sample-level metric。

---

## Slide 4 — Backbone Selection · Why NT-v2

老師可能會先問「為什麼是 NT-v2，不是 DNABERT 或其他？」我先回答這個。

**左 panel**：5M 訓練資料下的 controlled comparison，同樣的 task、同樣的 head、同樣的 LoRA 設定，**只換 backbone**。
- DNABERT-1 (2021, 91M params)：61.2%
- DNABERT-2 (2023, 119M params)：57.4%
- NT-v2 (2023, 498M params)：62.0% ← 我們選的（金色星號標 "Selected"）

5M 時 NT-v2 只勝 DNABERT-1 約 0.8 pp——差距其實不大。**但有兩個理由選 NT-v2**：

**右 panel**：NT-v2 從 500K 一路訓到 50M 的 scaling curve。Forward-only 從 55.3% → 62.0% → 64.5%，RC TTA 還能再加 1-2 pp。NT-v2 因為參數量大（498M），有足夠 capacity 吸收更多資料；DNABERT-1/2 在更早就 plateau。

**Takeaway**：在 5M 時三個 backbone 相當，但 NT-v2 的 scaling slope 最陡——所以我們選 NT-v2、然後做 50M 擴展。事後驗證在 50M 達到 64.45%（RC TTA 66%），確認選對。

DNABERT-2 反而比 DNABERT-1 退步，是因為它用 BPE tokenizer 而 DNABERT-1 是 6-mer——這個對照已經暗示了後面 Finding 1 的故事：**tokenizer 選錯，模型再大也救不回來**。

---

## Slide 5 — Finding 1: Tokenisation > Pre-training（headline finding）

左 panel 是 genus level（120 類），右 panel 是 species level（1535 類）。

**左 panel · Genus**：三根 bar，48.8% / 67.1% / 87.4%。
- 橙色雙箭頭：**+18.3 pp pre-training effect**——相同 6-mer tokenization 下，預訓練 vs 從頭訓練的差距。pre-training 確實有用。
- 綠色雙箭頭：**+20.4 pp tokenization effect**——預訓練 6-mer vs 從頭訓練 13-mer 的差距。**換個 tokenizer 就能贏過 100 倍大的預訓練模型**。

**右 panel · Species**：差距放大。
- 預訓練 6-mer NT-Species 17.8%
- 從頭訓練 13-mer MT 49.7%
- **+31.9 pp tokenization gap**

到 species level，tokenization 的影響直接決定模型有沒有實用價值。

下面綠色 takeaway：「**Pre-training 確實有貢獻，但無法補救一個 inadequate 的 tokenization 選擇**」。這就是我整篇論文最強的一句話。

---

## Slide 6 — Finding 2: Data > Tricks

第二個 finding 比較工程性，但對 thesis 完整性很重要。

**左 panel**：data scaling 曲線。500K → 5M 提升 7.76 pp，5M → 50M 又加 4.02 pp。雖然增益遞減，每個 10× 都還有意義。

**右 panel**：常見的訓練 trick 效果——logit adjustment、RC consistency、class-balanced sampler、LR tuning。**每個都只有 ±0.5 pp**。橫向綠色虛線是 data 10× 的 7.76 pp 增益——當對照基準看，trick 全部加起來都還不到 data 10× 的 1/4。

綠色 takeaway：**data scaling 比 hyperparameter tuning 強 10×**。意思是後面做這類研究的人，應該把時間花在資料規模上、不要花一兩個月調 trick。

---

## Slide 7 — Finding 3: Practical Utility Threshold

這張左邊是散佈圖、右邊是 mechanistic 解釋，圖文並列。

**左圖**：橫軸 read accuracy，縱軸 sample-level Pearson r。9 個 model 都標上去，可以看到一個明顯的「斷層」：
- 紅色橫帶（r < 0.2）是 **noise floor zone**——所有 NT-Species 配置跟 MT 6-mer 都卡在這
- 綠色直帶（read acc 40–50%）是**實用門檻**——MT 13-mer 剛好跨過、Kraken2 直接在右上角
- Kraken2 (66.2%, 0.727) 跟 MT 13-mer (50%, 0.47) 是唯二實用的點

**右側紅底 box**：noise floor 的 mechanistic explanation。
- 1535 物種、1K reads/sample，每個物種期望 0.65 reads
- 17.8% accuracy 下，誤分 reads 平均分散，每個物種被加 0.54 spurious reads → SNR ≈ 1
- 到 50% accuracy，noise 降到 0.33 reads/物種，信號才壓過噪聲
- 門檻：**~40–50% accuracy**

綠色 takeaway：**species abundance 要實用，必須過 ~40–50% threshold，6-mer NT-v2 跨不過去**。

---

## Slide 8 — Finding 4: Router Threshold (Monotonic)

這是 hierarchical pipeline 的一個 design insight。

**左圖 bar chart**：三個不同 router quality 對應的 species Top-1 變化：
- 紅色 -2.8 pp（MT 6-mer router 48.9%）：退步最多
- 橙色 -2.0 pp（NT-Genus router 66%）：退步
- 綠色 +1.12 pp（MT 13-mer router 87.5%）：提升

虛線標的 ~80% 是 **net-positive threshold**。Hierarchical masking 的效果是 **monotonic in router accuracy**。

**右側橙底 box · Intuition**：
- Router 對 → mask 移除錯誤候選 → 好
- Router 錯 → mask 排除正確物種 → 災難
- 兩個效果的 weighted average 由 router accuracy 決定

綠色 takeaway：**hierarchical pipeline 需要 router > ~80% 才會 net positive，不是 free-lunch 優化**。這個設計準則對未來做類似系統的人很有用。

---

## Slide 9 — Finding 5: Per-Genus Oracle Quantifies Tokenisation Gap

這張用 bar chart 把 NT-v2 各種配置跟 MT 13-mer 並排比較。

從左到右：
- NT-v2 flat：17.8%
- NT-v2 hier：15.8%
- NT-v2 per-genus（predicted router）：15.6%
- **NT-v2 per-genus（ORACLE, 完美 router）：29.5%** ← 6-mer NT-v2 的歷史最高
- MT 13-mer flat：49.7%
- MT 13-mer hier：50.9%

兩個視覺重點：
1. **橙色橫線標的 29.5%**：這是 NT-v2 在 6-mer 框架下的 ceiling，就算給它完美 genus router 都到不了 30%
2. **紅色雙箭頭 +21.4 pp**：MT 13-mer flat 49.7% 完全沒做 routing，已經比 NT-v2 完美 routing 還高 21 pp——**tokenization gap 比 routing architecture 還根本**

橙色 takeaway：**就算給 NT-v2 完美 router，6-mer 框架 ceiling 是 29.5%；MT 13-mer 完全不用 routing 達 49.7%，+20 pp 的 tokenization gap 直接量化在這裡**。

---

## Slide 10 — Finding 6: Kraken2 In-DB vs OOD

這張用三個 panel 同時呈現 Kraken2 對比的不同面向。

**左 panel · Species level radar**：三個 model 在 5 個 metric 上的綜合表現
- 金線 Kraken2：read acc、Pearson r、BC、Sens@95spec 都最大
- 綠線 MT 13-mer hier：只在 ROC AUC 贏 Kraken2（0.967 vs 0.925），其他都輸
- 藍線 NT-Species flat：整體最小

**中 panel · Genus level read accuracy**：四個 model 並排
- MT 6-mer genus 48.8%
- NT-Genus 67.1%
- **Kraken2 (in-DB) 69.5%** ← 跟 NT-Genus 幾乎一樣（差 2.4 pp）
- MT 13-mer 87.4%

旁邊金色斜體標注：**Kraken2 在 classified reads 上 genus precision 是 99.3%**——commit 的時候極準，但只 commit 70%。這個 precision/recall trade-off 是 k-mer 方法的特徵。

**右 panel · OOD bar chart**：In-DB vs OOD 比較
- Kraken2 in-DB 66.2% → OOD **0%**（紅色，標「DB 沒有 k-mer 可比對」）
- Neural models 維持 low-but-non-zero signal on OOD

金色 takeaway：**learned methods 跟 k-mer matching 是 complementary，不是 competitor——它們對應不同的 deployment regime**。In-DB simulated reads 是 Kraken2 強項；OOD novel organisms 是 neural 強項。

這張其實是我整篇論文最重要的 positioning，直接回應「為什麼不用 Kraken2 就好」這個 reviewer 必問的問題。Genus 跟 species 兩個層級的數字都列出來，避免老師覺得我只挑對自己有利的 task 比較。

---

## Slide 11 — Complete Results Matrix

把所有結果整成一張 color-coded 表格。

紅色行 = 退步或卡 noise floor（NT-v2 各種變體、MT 6-mer）；橙色行 = oracle ceiling；綠色行 = MT 13-mer 跨過實用門檻；**金色 Kraken2 兩行 = species + genus 都列出**；底下紅字 = Kraken2 OOD 0%（critical limitation）。

整張表的故事性其實就排出來了：上半部所有 NT-v2 配置被 30% 鎖死，中間 MT 6-mer 證明從頭訓練 + 6-mer 沒得救，下面 MT 13-mer 用 13-mer 從頭訓練破解，最底 Kraken2 在 in-DB 最有利情境贏（species 66.2%、genus 69.5%）但 OOD 完全失效。

**Kraken2 兩行的對比**：Pearson r 從 species 0.727 → genus 0.844、BC 從 0.218 → 0.178、ROC AUC 從 0.925 → 0.895（注意 genus 的 ROC 反而稍低，跟 species 一樣是 1K reads/sample 的取樣噪聲造成，跟模型本身無關）。Genus 因為 class 數量少，sample-level 指標普遍比 species 漂亮。

藍底 takeaway：「**同 DB、同 data、同 protocol**」——強調這是 controlled comparison，不是 cherry-picked 比較。

---

## Slide 12 — The Unifying Story

把六個 finding 整合成一條 story arc。

圖上是四個 hypothesis box，從左到右：
- **H1: 參數量** → Refuted（紅）。NT-v2 498M 慘輸 5M 的 MT 13-mer。
- **H2: Pre-training** → Helps but...（橙）。Genus level +18 pp、species level 不夠。
- **H3: Routing design** → Bounded（橙）。NT-v2 完美 routing ceiling 29.5%，還是輸 MT 13-mer flat 49.7%。
- **H4: Tokenization** → Confirmed（綠）。+31.9 pp 直接 fix。

下方綠斜體：「**Tokenisation is the hidden bottleneck**」。

藍色 takeaway：foundation model 文獻通常強調 scale 跟 pre-training，**tokenization 很少被拿來做 ablation**——我們的研究正好把這個變數隔離出來，這在 ML 領域跟 bioinformatics 領域都不常見。

---

## Slide 13 — Contributions

四個 standalone contributions，用 4 個有編號 badge 的 card 排版：

**(1) Controlled 3-axis ablation** — 同 data、同 test、同 protocol，識別 tokenization 為 species-level dominant factor。
**(2) Quantitative noise-floor analysis** — 非線性 utility 曲線、~40-50% threshold、SNR 模型解釋。
**(3) Router quality threshold theorem** — 三個 router quality 的 monotonic 證據，~80% 是 net-positive 門檻。
**(4) Same-DB Kraken2 + OOD analysis** — Kraken2 in-DB 66%、OOD 0%，建立 learned/k-mer 的 complementary positioning。

四個都可以單獨拿出來賣，也可以一起賣（thesis 整合版）。

---

## Slide 14 — Publication Direction

用 comparison matrix 對比三個選項，每欄一個 venue：

| | Bioinformatics journal | ML workshop | Thesis only |
|---|---|---|---|
| Effort | Medium 8 週 | Medium-High 10 週 | Low |
| Best fit | Same-DB Kraken2 + OOD + sample-level | Tokenization > pre-training ablation | 完整 narrative |
| Risk | Reviewer 要 real dataset | ML 審查可能要更大實驗 | 學術曝光度低 |
| My ranking | ★★★ Primary | ★★ Secondary | ★ Baseline |

金色 takeaway：**先 Bioinformatics（主）→ 被 reject 再轉 ML workshop → Thesis 是保底**。

---

## Slide 15 — Strengths & Weaknesses

兩欄並排，誠實列。

**綠色 Strengths**：
- Same-data 三軸 ablation——unusually clean
- Sample-level metrics 連到真實 workflow
- Same-DB Kraken2 baseline 直接 close 掉「為什麼不用 Kraken2」這個 objection
- Mechanistic story（noise floor、router threshold）不只 empirical
- Per-genus oracle 量化 tokenization gap

**紅色 Weaknesses + 橙色 Mitigations**：
- Simulated reads only → 補 HMP mock community 做 sanity check
- 只 2505 個基因組 → 投稿時 frame 成 "controlled study"，承認 scope
- 沒有 paired-end / error / coverage tests → 同上 framing
- Foundation model 偏小（498M）→ 我們的賣點不是 scale，是 scale-agnostic finding

金色 takeaway：**framing 成 "controlled comparison study" + 補 1 個 real-dataset sanity check**。這兩個 mitigation 結合起來可以解掉大部分 reviewer 質疑。

---

## Slide 16 — Timeline + 4 Questions

上半部是 timeline：
- **Now（5月）**: thesis 135 頁、所有結果到齊
- **6/15**: mock defense + 簡報
- **7–8月**: rewrite chapter 4 → Bioinformatics 期刊稿
- **8/31**: submission 目標
- **9–12月**: first-round review
- **2027 Q1**: revision / accept

下半部是四個請教老師的問題，每個用色塊 card：

- **Q1**（綠）: Bioinformatics 期刊當 primary venue，老師同意嗎？或老師有偏好的其他 journal？
- **Q2**（藍）: Real-dataset validation——投稿前必須補，還是 post-defense 補進 v2？
- **Q3**（橙）: ML workshop（Option B）值不值得花力氣？還是專心 bioinformatics community？
- **Q4**（金）: 老師有沒有想要 included 的 collaborator 或 dataset？

---

## 給自己的 Backup Q&A（口頭備援，老師問再用）

### Q: Kraken2 對比會不會讓你的 paper 顯得弱？
A: 完全相反。Kraken2 in-DB 贏是預期內的——這正是 k-mer 方法在 simulated reads 上的強項。我們的賣點不是「贏 Kraken2」，而是：(a) controlled ablation 揭露 tokenization 的關鍵性、(b) Kraken2 OOD 0% 對應 k-mer 方法的根本盲點、(c) sample-level metrics 提供更貼近實際應用的對比。Kraken2 那一列其實是**強化論點**。

### Q: Real dataset 怎麼補最快？
A: HMP mock community 最快——已 publicly available、ground truth 已知、reads 條件跟我們訓練資料接近。1-2 週內可以補完。若要更嚴格，可以用 published MAG-rich gut sample，但 ground truth 取得會更花時間。

### Q: Foundation model 投 ML venue 的話 model size 不會太小？
A: 我們的 framing 不是「scale up foundation model」，而是「即使 scale 不變，tokenization 是 dominant factor」。這個 framing 對 ML audience 有意義——現在 LLM 領域大家都假設「scale wins」，DNA foundation model 我們的研究反證了至少在 species classification 任務上不是這樣。

### Q: Per-genus oracle 29.5% 跟 thesis 寫的 27.8% 不一樣？
A: 27.8% 是含 selective subgenus routing 的版本，29.5% 是不含 subgenus 的乾淨版本。新數字 29.5% 是 cleaner 的 ceiling，我會把 thesis 統一更新。

### Q: 為什麼 NT-v2 hier 比 flat 差？跟 thesis 寫的 router threshold 故事一致嗎？
A: 完全一致。NT-Genus router 66% 在我的 threshold 模型下是 "below threshold"——hier 必然 net negative。MT 13-mer router 87.5% 才在 threshold 之上、才會 net positive。三個 router quality 的 monotonic 趨勢是直接證據。

### Q: 時間軸跟畢業期限有衝突嗎？
A: 6/15 學位口試、6/30 thesis 定稿，期限沒問題。7-8 月再開始寫 paper，9 月若投出，年底有 first review，隔年初做 revision，2027 Q1 出結果。整體時程是合理的。

---

## Slide-to-Time 對照

| Slide | 內容 | 預計時間 |
|---|---|---|
| 1 | Title | 30 sec |
| 2 | Problem | 1.5 min |
| 3 | Three families | 2 min |
| 4 | **Backbone Selection** | **2 min** |
| 5 | Finding 1 (headline) | 3 min |
| 6 | Finding 2 (data) | 1.5 min |
| 7 | Finding 3 (threshold) | 2.5 min |
| 8 | Finding 4 (router) | 2 min |
| 9 | Finding 5 (oracle) | 2 min |
| 10 | **Finding 6 (Kraken2 + genus)** | **3 min** |
| 11 | Matrix | 1.5 min |
| 12 | Story arc | 2 min |
| 13 | Contributions | 1.5 min |
| 14 | Publication | 2 min |
| 15 | Strengths/Weaknesses | 2 min |
| 16 | Timeline + Q&A | 3 min |
| **Total** | | **~32 min** |

留 10–15 分鐘給老師討論四個問題。
