# Weekly Meeting · 2026-06-02 · 中文逐字稿

對應簡報：`docs/slides/meeting_2026_0602.pptx`（10 張）
建議時間：15-20 分鐘 + 5-10 分鐘討論
語氣：5/28 後第二週進度——前一週 (5/31 deck) 處理 MT alignment + 發現
inversion；這一週做 GitHub 整理 + Nano4 onboarding + 收 Per-genus 13-mer。

---

## Slide 1 — Title · Weekly Progress · Updates Since 5/28

老師好。今天是 5/28 那次 meeting 之後的第二週進度。

第一週 (5/28-30) 主要是 MT predictions 順序對齊、發現 species/genus inversion、
thesis 跑到 139 頁，這部分上週 5/31 deck 報告過了。

這一週 (5/31-6/2) 三件事：
1. Per-genus 13-mer Exp F 從 Taiwana-2 拿到——55.93%，補上 router quality 的第三個 data point
2. 整個 codebase 整理成 GitHub repo，四個環境（TWCC、Taiwana-2、本地、Nano4）都同步
3. Nano4 H200 免費 1 個月——已 onboarding，但 sanity check 遇到 transformers 版本問題

整個 deck 10 張，預計 15-20 分鐘。

---

## Slide 2 — Progress Timeline · 5/28 → 6/2

整個 2 週進度。時間軸從左到右：

- **5/28**: advisor meeting，列了 6 個 decision points
- **5/29**: MT 5/6 個 predictions 從 Taiwana-2 對齊到 reads_100K.fa 順序；做完 in-DB 比較表，發現 **genus level MT 13-mer 反超 Kraken2**
- **5/30**: thesis 從 137 → 139 頁；同一天 TWCC iService 額度耗盡（-802.5 點），sbatch 開始 fail
- **6/1**: 整理 GitHub repo (`m2lab-ntu/gfm-classifier`)，4 個環境 STATUS.md 全部填好；同時 Taiwana-2 送來 Per-genus 13-mer Exp F 預測：**55.93% read accuracy**
- **6/2**: Nano4 (H200) 拿到一個月免費試用，env 設好、data 從 Nano5 rsync 完成；但 sanity check 兩次 fail
- **現在**: 等 Nano4 unblock 解 transformers 版本問題（~1 hr 內可解），接著開始 P0

底下藍底 box 解釋目前 blocker：**Nano4 transformers 版本太新**，NT-v2 backbone (基於 ESM) 用的 `find_pruneable_heads_and_indices` 在 transformers 4.36+ 被移除了。Fix：`pip install transformers==4.35.2`。

---

## Slide 3 — MT Alignment Fix

這張是上週的內容，主要為了 reference。MT predictions 之前 read 順序跟 reads_100K.fa
不一致，因此 in-DB mask 套不上。Taiwana-2 重跑後對齊。

左 panel: species level 對比——MT 13-mer flat 從 49.7% → **53.7%**（在 canonical
TWCC 100K test 上），MT 6-mer 變化很小。

右 panel: genus level 對比——MT 13-mer genus 從 87.4% (5M val pool, 50K rps) →
**94.25%** (100K test, 1K rps)。test set 跟取樣條件不同，重點是新數字跟其他所有
模型在同一個 evaluation 條件下。

下面綠 takeaway: **所有 MT in-DB 指標現在都正確算在 canonical 100K test set 上**。

---

## Slide 4 — Species/Genus Performance Inversion (上週發現)

這也是上週發現、補在這裡作 reference。in-DB fair-restricted 設定下：

**左 panel · Species level (1535 classes)**: Kraken2 主導
- Kraken2: 77.18% / r 0.847
- MT 13-mer flat: 52.64% / 0.514
- Kraken2 領先 **+24 pp**

**右 panel · Genus level (120 classes)**: MT 13-mer 反超
- MT 13-mer genus: 94.89% / r 0.9993 ← 最高
- Kraken2: 77.68% / 0.823
- MT 13-mer 領先 **+17 pp**

這個 inversion 補強 thesis 的「complementary」論點。

---

## Slide 5 — Why the Inversion (機制解釋)

機制：Kraken2 commit rate 70%，30% unclassified。

- Species level (1535 classes)：30% 分散到 1535 個 species，每個約 -0.2 reads → 影響小
- Genus level (120 classes)：30% 集中到 120 個 genus，每個約 -2.5 reads → 影響大

MT 13-mer 對所有 reads 都給 prediction，所以在 low-cardinality task 反而完勝。

---

## Slide 6 — Thesis Updates Summary

左欄 What changed:
- Table 4.29 MT 那幾行換成 aligned 版本
- MT 13-mer hier 那行標 N/A（checkpoint 損壞）
- 修正 OOD framing → deployment coverage asymmetry

右欄 What was added:
- 新 Table 4.30：fair-restricted comparison
- 三段討論段落（restriction 原因、inversion 解釋、coverage dependence）

頁數：137 → 139。

---

## Slide 7 — Blocker · TWCC Budget vs Nano4 Unblock

這張是這週狀況最大變化的一張。**雙 banner**：

**紅** · TWCC (Nano5) wallet -802.5 點，5/30 開始無法 sbatch 新 job
**綠** · Nano4 H200 **免費 1 個月**，repo 已 clone、env 已 setup、data 已 rsync，但 sanity check 卡住

三欄分析：

**綠 · Done (no GPU)**:
- GitHub repo 已 publish
- 4 個 env STATUS.md 都填好
- Thesis 139 pp 含 Table 4.30
- Per-genus 13-mer (55.93%) 拿到

**藍 · In progress on Nano4**:
- Env setup (conda + deps + data) ✓
- Sanity check ✗ (transformers 版本不對)
- 需要：降級 transformers 到 4.35.2
- 需要：sync DNABERT-2 last.pt 來 resume

**金 · Once Nano4 unblocked**:
- DNABERT-2 50M resume (36 hr H200)
- Speed/memory benchmark (3 hr)
- HMP real-dataset (3 hr)
- Per-genus 13-mer realign

下面紅色 takeaway: **TWCC 預算問題用 Nano4 解決，不需要老師加值**。

---

## Slide 8 — 6 Decisions · Status Update

5/28 列的 6 個 decision points，今天 status:

- **Q1** (DNABERT-2 resubmit): GREEN — 計畫**搬到 Nano4 H200 跑**（不用 TWCC 加值），等 Nano4 sanity check 解決即可
- **Q2** (DNABERT-1 50M 取消): RED — 維持取消建議，5M 數據 + 訓練成本論證已足
- **Q3** (MT 13-mer hier 重訓): ORANGE — 待老師決定（thesis 已標 N/A）
- **Q4** (Speed benchmark): GREEN — 改在 Nano4 統一 H200 上做（vs 之前 TWCC）
- **Q5** (258M training): RED — 維持不做建議，用 log-fit 外推取代
- **Q6** (HMP real-dataset): GREEN — Nano4 sanity check 後排隊執行

關鍵變化：**Nano4 出現讓 Q1、Q4、Q6 從「卡在預算」變成「卡在 Nano4 sanity check」**，
而 sanity check 是 1 小時就能解的工程問題，不是策略問題。

---

## Slide 9 — Recommended Priorities · Next 2 Weeks

按算力需求分三層。

**綠 · Immediate (CPU only)**:
- Per-genus 13-mer (Exp F) 在 Taiwana-2 重跑（read order 對齊）→ 補進 Table 4.30
- Thesis figure 重生（用新 aligned MT 數字 53.7%、94.25%）
- Thesis Section 4.13 校稿
- MT 13-mer hier 重訓 (Q3 decision)

這些都不需要 Nano4，可以立刻做。

**金 · After Nano4 unblock (~45 GPU-hr, FREE)**:
- DNABERT-2 50M resume from epoch 17 (36 hr H200)
- Migrate MT models from Taiwana-2 → Nano4
- Speed/memory unified benchmark on H200 (3 hr)
- HMP mock community inference (3 hr)

加總 45 GPU-hr，**全部 Nano4 免費 1 個月內輕鬆 cover**。

**紅 · Not doing**:
- DNABERT-1 50M 繼續 (~300 GPU-hr / 13 天，CP 太低)
- 258M 完整訓練 (~290 GPU-hr / 18 天，log-fit 預測 +4.2 pp 不影響結論)

---

## Slide 10 — Asks for Today's Meeting

三個 decision 請老師確認：

**Q1 (綠) · Migration plan: Nano4 takes over**
確認 Nano4 (H200, 免費 1 個月) 替代 TWCC 當主要 GPU 環境。DNABERT-2 resume 在 Nano4 跑、
TWCC 暫停、Speed benchmark 在 H200 統一做。可以嗎？

**Q2 (紅) · DNABERT-1 50M 最終決定**
取消。用 5M accuracy (61.78%) + 11.7 hr/epoch（vs NT-v2 2.8 hr）的訓練成本對比，
當作 deployment limitation 證據寫進 thesis。同意嗎？

**Q3 (金) · Per-genus 13-mer Exp F 整合**
Taiwana-2 送來對齊版預測後，把 55.93% 加進 Table 4.30 第 4 列，作為 router-quality
threshold 第三個 monotonic data point（87.5% router 在 per-genus pipeline 也驗證
+2.23 pp gain）。可以嗎？

---

## 給自己的 backup Q&A（口頭備援）

### Q: 為什麼 Nano4 sanity check 一直 fail？
A: 兩次 fail 原因不同。第一次是 `heads.py` 模組缺失——重 clone 時忘了把這個檔案放
進 selective_copy.sh 的 whitelist。已補上。第二次是 transformers 版本問題：NT-v2 用
ESM-2 backbone，依賴 `transformers.pytorch_utils.find_pruneable_heads_and_indices`，
這個在 transformers 4.36+ 被移除。Fix 是 `pip install transformers==4.35.2`，1 小時內
可解。

### Q: Nano4 免費 1 個月，到期後怎辦？
A: 1 個月內可以跑完所有 P0 任務（DNABERT-2 resume 36 hr、speed benchmark 3 hr、
HMP 3 hr，加總不到 45 GPU-hr）。1 個月後若需要更多算力，可以申請 TWCC 加值
或評估其他 cluster。但 thesis 跟 paper 主要實驗應該在這 1 個月內收尾。

### Q: GitHub repo 整理是不是花太多時間？
A: 花了大概半天但效益很大：(a) 4 個環境共用一份 code，不再有同步亂掉的問題；
(b) Nano4 上 git clone 一句就 setup 環境；(c) 投稿時 paper 寫 GitHub URL
直接引用；(d) 老師也可以 https://github.com/m2lab-ntu/gfm-classifier 看當前狀態。

### Q: TWCC 額度真的不需要加值嗎？
A: 短期不需要——Nano4 一個月內可以 cover P0 + P1。長期看：如果 8 月之後做 paper
revision 需要新實驗，那時看是否要回 TWCC 加值，或繼續用其他 cluster。

### Q: Per-genus 13-mer 55.93% 跟 57.20% 哪個對？
A: 兩個都對，只是分母不同。**55.93%** = 55,930/100,000（unclassified 算錯，跟其他模型
口徑一致），**57.20%** = 55,923/97,767（只看 routed reads，類似 Kraken2 classified-only）。
Thesis 表用 55.93% 跟其他列一致。

### Q: 為什麼 Per-genus 13-mer 反而比 flat 高 2 pp？這跟之前 NT-v2 hier 反而比 flat 低不一致？
A: 完全一致！這就是 **router quality threshold theorem** 的證據：
- 66% router (NT-Genus) → hier 比 flat 低 (-2 pp)
- 87.5% router (MT 13-mer) → hier 比 flat 高 (+1.12 pp read level / +2.23 pp per-genus)
- 48.9% router (MT 6-mer) → hier 比 flat 低更多 (-2.8 pp)
三個 router quality 完美 monotonic，theorem 成立。

---

## Slide-to-Time 對照

| Slide | 內容 | 時間 |
|---|---|---|
| 1 | Title + 兩週進度概覽 | 1 min |
| 2 | Progress timeline | 1.5 min |
| 3 | MT alignment fix (上週) | 1 min |
| 4 | Inversion finding (上週) | 1.5 min |
| 5 | Why inversion (上週) | 1 min |
| 6 | Thesis updates (上週) | 1 min |
| 7 | TWCC vs Nano4 budget | 3 min |
| 8 | 6 Decisions status | 2.5 min |
| 9 | Recommended priorities | 2 min |
| 10 | Asks Q1-Q3 | 2 min |
| **Total** | | **~17 min** |

留 8-13 分鐘給老師討論 Q1-Q3。
