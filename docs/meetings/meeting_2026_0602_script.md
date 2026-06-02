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

## Slide 7 — Blocker · TWCC Budget vs Nano4 Partition Rules

這張是這次最重要的「重新評估」slide。

**上方雙 banner**：
- 紅 · TWCC (Nano5) wallet -802.5 點，5/30 開始無法 sbatch 新 job
- 綠 · Nano4 H200 **免費 1 個月**，220 nodes × 8 H200 = 1,760 顆 GPU 的大 cluster

**Nano4 Slurm partition 表（重點）**：

| Partition | Max time | Min GPU | 用途 |
|---|---|---|---|
| `dev` | **1 hr** | 1 GPU OK (no limit) | inference / benchmark / eval / realign ✓ |
| `normal` | 12 hr | **min 64 GPU (8 nodes)** | 訓練 — 但要 DDP-ported 才能跑 ⚠ |

兩個 partition 每位 user 各 5 running + 5 pending。

**底下金色 box · 對我們 pipeline 的影響（這是這頁的核心）**：

1. **Inference / eval / sample-level benchmark**（NT-v2、MT、DNABERT-2 eval）— 全部塞得進 dev 1 hr 上限 ✓
2. **DNABERT-2 50M resume** — 單 GPU、用 dev 接力 resubmit ~3-4 天 wall clock（auto-resume 已內建）
3. **258M training（如果要做）**— **需要 DDP port，1-2 天工程**，然後 64 H200 上 ~3 hr；OR 不可行

關鍵句：**Nano4 normal partition 要 64 GPU 起跳，我們現有單 GPU 訓練 script 跑不上去**。要嘛接受 dev 1 hr 接力，要嘛改寫成 DDP 分散式。

這個 partition 限制完全改變 258M 跟其他訓練任務的可行性評估。Slide 8 跟 9 會展開。

---

## Slide 8 — 6 Decisions · Status Update (含 Nano4 重新評估)

5/28 列的 6 個 decision points，套用 Nano4 partition 限制後更新：

- **Q1** (DNABERT-2 50M resume): GREEN — Nano4 dev partition 36 個 1 hr job 接力（auto-resume）→ ~3-4 天 wall clock，**不需改 code**
- **Q2** (DNABERT-1 50M 取消): RED — Nano4 dev 接力的話 5× 慢於 DNABERT-2，要 ~10 週 wall clock，**確認取消**
- **Q3** (MT 13-mer hier 重訓): ORANGE — 跟 Nano4 partition 無關（在 Taiwana-2 V100 上跑），等老師決定
- **Q4** (Speed/memory benchmark): GREEN — inference 在 Nano4 dev (1 hr 綽綽有餘)，不需 DDP
- **Q5** (258M training): ORANGE — **重新評估！** 從「18 天 wall clock 不可行」變成「DDP port 1-2 天工程 + ~3 hr 訓練可行」，但**+4.2 pp 仍不影響結論**——值不值得？
- **Q6** (HMP real-dataset): GREEN — inference 在 Nano4 dev，不需 DDP

**Q5 的重新評估是這頁重點**。原本我們的反對理由是「太久」，現在 partition 細節改變了 → 變成「engineering 成本 1-2 天，但科學價值未變」。要老師重新判斷是不是值得花這 1-2 天。

---

## Slide 9 — Recommended Priorities · 分四層（依 Nano4 partition 適用性）

按「能不能跑、要多少工程」分四層：

**綠 · Now (Taiwana-2 / CPU — 不用 Nano4)**:
- Per-genus 13-mer (Exp F) 在 Taiwana-2 重跑（read order 對齊）→ 補進 Table 4.30
- Thesis figure 重生（用新 aligned MT 數字 53.7%、94.25%）
- Section 4.13 校稿 · 選擇性 MT 13-mer hier 重訓 (Q3)

立刻可做，不卡 Nano4。

**藍 · Fits Nano4 dev partition (1-hr jobs, 單 GPU)**:
- Sanity check NT-Species inference — **BLOCKED**，先 `pip install transformers==4.35.2` 修
- DNABERT-2 50M resume — 36 個 dev 接力 job + auto-resume (~3-4 天 wall clock)
- Speed/memory unified benchmark on H200 (~30 分鐘)
- HMP mock community real-dataset inference (~30 分鐘) — paper prep

dev partition 限制 1 hr，inference jobs 都很短不是問題，training resume 用 auto-resume 機制每 hr 接續一次也行。**這些都不需要改 code**。

**金 · 需要 DDP port 才能跑（1-2 天工程）**:
- 258M training (genus + species) — 改寫 train.py 成 DDP 分散式，然後 ~幾 hr 在 64 H200 上完成。
- **價值評估**：log-fit 預測 +4.2 pp，**跨不過 tokenization gap (MT 13-mer 87.4%)**，不會改變 thesis 結論。
- → Cost-benefit: 1-2 天工程換 marginal accuracy improvement，**老師決定**

**紅 · 不做**:
- DNABERT-1 50M — 5× 慢於 DNABERT-2，dev 接力要 ~10 週 wall clock，不切實際

---

## Slide 10 — Asks for Today's Meeting

三個 decision 請老師確認：

**Q1 (綠) · 用 Nano4 dev partition 跑我們 pipeline**
Nano4 normal 要 64 GPU 起跳（DDP-only），但我們所有 inference 任務 + DNABERT-2 resume
都塞得進 dev (1 hr / job, 5 concurrent)。Speed benchmark、HMP、Per-genus realign 全部
夠用。**確認走 dev partition 路線（不改 code）可以嗎？**

**Q2 (橙) · 258M training — 要不要花 1-2 天工程做 DDP port？**
重新評估：Nano4 normal 64 H200 + DDP 可以讓 258M 訓練從「18 天 wall clock」變成「1-2 天工程 + 幾小時訓練」。
**但科學價值未變**——log-fit 預測 +4.2 pp，跨不過 MT 13-mer 87.4% 的 tokenization gap。
這 1-2 天工程值得嗎？或是把這時間花在 paper writing / HMP validation 更好？

**Q3 (金) · Per-genus 13-mer Exp F 整合**
Taiwana-2 送來對齊版預測後，把 55.93% 加進 Table 4.30，作為 router-quality threshold
第三個 monotonic data point（87.5% router 在 per-genus pipeline 驗證 +2.23 pp gain）。同意嗎？

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

### Q: Nano4 normal partition 為什麼要 64 GPU 起跳？這是什麼設計？
A: 晶創 26 (Nano4) 是 HPC scale 設計，每 node 8 H200 + 8 InfiniBand 400 Gbps。
normal partition 設計給大規模 distributed training（LLM pre-training 等級），最小單位是
8 個 node = 64 GPU。我們現有 single-GPU LoRA fine-tuning 不在這個 use case，要嘛
適應 dev (1 hr 上限) 要嘛改寫成 DDP。

### Q: 為什麼我們的 code 不是 DDP？
A: NT-v2 + LoRA + 50M dataset 在單顆 H100 上 14 hr 跑完，沒必要 distributed。
DDP overhead（NCCL init、gradient all-reduce、checkpoint coordination）對小 model 反而
拖累。設計時的 trade-off。現在 Nano4 normal 強制 64 GPU 才暴露這個 mismatch。

### Q: DDP port 真的要 1-2 天嗎？
A: 嚴格的估算：
- DistributedSampler、DDP wrap、torchrun init: 半天
- per-rank logging、rank-0 only checkpointing: 半天
- 多 node debug (NCCL config、network config): 0.5-1 天
- Sanity check 在 8 node 確認 loss 跟單 GPU 一致: 0.5 天
總計 1-2 天。但這個 code 改完之後可以重複用，是 reusable infrastructure investment。

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
