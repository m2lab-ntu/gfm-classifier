# Weekly Meeting · 2026-06-09 · 中文逐字稿

對應簡報：`docs/slides/meeting_2026_0609.pptx`（8 張）
建議時間：12-15 分鐘 + 5-10 分鐘討論
語氣：上週 (6/2) Nano4 剛 onboarding 但 sanity check fail；這週 sanity check 通過、
6 個工程修正、所有 P0 腳本就緒，今天 meeting 的目標是確認三個待決 decisions。

---

## Slide 1 — Title

老師好。今天是 6/9，對應上週 6/2 那次 meeting 之後的一週進度。

上週 meeting 結束時最大的 blocker 是 Nano4 的 sanity check 失敗——transformers 版本
不相容。這週的核心任務就是把 Nano4 完全打通，然後把所有 P0 實驗腳本準備好，
等老師今天確認幾個 decisions，下週就可以出數字。

這個 deck 8 張，大概 12-15 分鐘。

---

## Slide 2 — 進度時間軸

這張時間軸從上週 6/2 advisor meeting 一直到今天。

6/2 meeting 結束後，我先把 Nano4 環境問題解掉：
上週 sanity check 失敗是因為 ESM-based NT-v2 backbone 用的一個函數
`find_pruneable_heads_and_indices` 在 transformers 4.36 之後被移除了。
修法是把那個函數直接 patch 回 HuggingFace cached model 的 modeling_esm.py，
而不是降版本——這樣其他 downstream 的 package 相容性不受影響。

6/3 sanity check 通過，Job 71907。NT-Species sp_v4 在 Nano4 H200 的結果是 17.83%，
跟 TWCC 的 17.83% 完全一致，差距小於 0.01%——代表整條 pipeline 移植成功。

接下來 6/3 到 6/7 這段時間，我做了 6 個工程修正，詳細等 slide 6 再說。
重點是 DNABERT-2 的 resume 腳本跟 MT benchmark 腳本都完成了，現在是「萬事俱備，
只欠 rsync」的狀態。

---

## Slide 3 — Nano4 Migration 狀態

左邊是 migration checklist。
打勾的部分：SSH、conda env、git clone、50M 訓練資料、100K 測試資料、NT-v2 checkpoint、
sanity check——全部搞定。

黃色圈圈的部分是還沒完成的：
- DNABERT-2 last.pt 需要從 Nano5 rsync 過來，473 MB，
- MT models 需要從 Taiwana-2 rsync 過來，給 benchmark 用，
- HMP mock community FASTQ 需要從 SRA 下載。

這三件事的 rsync 指令我都寫好了，等一下 meeting 確認好方向就可以直接跑。

右邊是硬體規格跟 sanity check 結果。
H200 有 143 GB HBM3e，比 H100 的 96 GB 多了 50%，所以 batch size 可以開更大，
推論速度預計比 TWCC 快 20-30%。

底部綠框是 Job 71907 的結果：1 分 32 秒跑完 100K reads，batch_size=1024，
跟 TWCC baseline 完全 match。

---

## Slide 4 — P0-A: DNABERT-2 50M Resume

DNABERT-2 之前在 TWCC 跑到 epoch 17 就因為 48 小時的 wall time 卡住了，
val_acc 是 59.22%。

左邊是 resume 狀態：已經做了 57% 的訓練，還剩 13 個 epoch。
在 H200 上，每個 epoch 估計比 H100 快 20-30%，
dev partition 每次 1 小時，預計需要 5-7 次 resubmit 就可以跑完。
腳本是 `run_dnabert2_genus_50M.nano4.sh`，每次跑完會自動存 last.pt，
下次 sbatch 就從 last.pt 繼續——完全自動化。

唯一的 blocker 是 last.pt 還在 Nano5，需要 rsync 過來，473 MB。

右邊是完成後的比較圖（預估）。現在的已知數字：
MT 13-mer genus 94.25%、Kraken2 in-DB 77.68%、NT-v2 LoRA 64.45%、
DNABERT-2 5M RC TTA 58.88%。DNABERT-2 50M 的最終結果估計在 62% 左右，
星號標示是估算。跑完後用 RC TTA eval 得到最終數字。

這個實驗對論文的意義是：補上 50M data scale 下的 DNABERT-2 baseline，
讓 Table 4.x 的比較更完整。

---

## Slide 5 — P0-B: MT Speed/Memory Benchmark

這張說明 benchmark 的設計。

左邊是 6 個要測的模型：
MT 13-mer genus、MT 6-mer genus、MT 13-mer species、MT 6-mer species、
NT-v2 sp_v4、DNABERT-2（等訓練完）。
測三個指標：throughput（reads/sec）、latency（ms/read）、peak GPU（MiB）。

右邊說明為什麼這個 benchmark 對論文和投稿重要：
MT 只有 5M 參數，是 NT-v2 的 1/100，這個速度優勢是論文的核心賣點之一。
要投 Bioinformatics 的話，需要有具體的 reads/sec 跟 GPU memory 數字來支撐
「practical deployment」的 claim。另外，6-mer 跟 13-mer 的速度差異也很有趣——
13-mer 每個 read 的 token 數更少（因為 stride 更大），理論上推論應該更快，
但 vocabulary 是 4096 vs 4^6=4096... 嗯，其實 vocab 一樣，差別在 token 數量。
這個要實測才知道。

Blocker 一樣是 MT models 需要從 Taiwana-2 rsync 過來。
一旦 rsync 完成，`run_mt_benchmark_nano4.sh` 一個 sbatch 可以跑完所有 6 個模型，
一個 dev job 1 小時搞定。

---

## Slide 6 — Engineering Highlights

這週做了 6 個 commits，都是讓 Nano4 pipeline 能跑起來的必要修正。

**peft key remap**：peft 0.6 以後把 LoRA weight 的 key 從 `query.weight` 改成
`query.base_layer.weight`。我在 train.py 的 resume 路徑加了自動 remap，
讓舊的 TWCC checkpoint 可以在 Nano4 的新 peft 版本上直接 load。

**vocab size mismatch**：MT 13-mer genus 的 checkpoint embedding 是 4097 × dim，
但 tokenizer 只有 4096 個 token。多出來的那一行是訓練時的 artefact。
在 extract_mt_predictions 加了 truncate/pad 處理。

**data_loader.py 補進 repo**：這個檔案之前只在 TWCC local 有，沒有 commit 進去，
導致 Nano4 跑不起來。現在補進 scripts/ 了。

**PYTHONPATH / sys.path 修正**：extract_mt_predictions 用 sys.path.insert 加了
MetaTransformer src，但這樣會遮蔽 MT 自己的 utils package，造成 import 衝突。
修了 import 順序。

**device_handler init**：MT 的 device_handler 需要在 `model.to(device)` 之前先顯式
初始化，否則 benchmark loop 裡第二個 model 會 crash。另外加了 `time_limit_sec`
參數，讓訓練在快超時之前自動存 checkpoint。

**resource_monitor.py**：新增的腳本，每 N 秒 log 一次 GPU memory 跟 CPU 使用率，
給 benchmark 量測 peak GPU MiB 用的。

這些修正全部都是 blocker——沒有這些，Nano4 上的任何一個 job 都會 fail。

---

## Slide 7 — Decision Board

這張是今天 meeting 最重要的一張。

**已解決**兩件：
- TWCC budget 問題：Nano4 免費 1 個月可以蓋掉所有剩餘的計算需求，不需要再替 TWCC 充值。
- Nano4 onboarding：sanity check 通過，pipeline 一致。

**待決三件**，需要老師今天給方向：

**Q1：DNABERT-1 50M** — 之前在 TWCC 跑到 epoch 4，每個 epoch 要 11.7 小時，
非常慢。在 Nano4 dev partition 要跑完 30 epochs 大概需要 350 次 resubmit，
不太實際。我的建議是直接取消，用 5M 的結果（61.78% RC TTA）做論文的 reference。
但如果老師覺得 50M DNABERT-1 是重要的 baseline，我可以研究看看有沒有更快的方法。

**Q2：MT 13-mer hier 重跑** — Taiwana-2 上的 checkpoint 訓練到一半 corrupted，
val_loss 跳到 9.29。重跑需要 Taiwana-2 V100 約 1-2 天。完成後可以補上 Table 4.29
最後一行，多 2-3 pp 的數字。如果 6/15 要 defense，這件事需要這週就決定跑不跑。

**Q3：HMP mock community inference** — 下載 SRR072232（約 1-2 GB），
跑 NT-v2 sp_v4 推論，然後跟 known staggered abundance 算 Pearson r 跟 Bray-Curtis。
這是「real metagenomic data」的 validation，對投稿比較有說服力。
如果目標是 6/30 論文繳交前把結果塞進去，這週就要啟動。

---

## Slide 8 — Next Steps

最後整理 6/9 到 6/15 defense 這一週的計畫。

**這週優先**：
- P0-A：rsync DNABERT-2 last.pt 到 Nano4，開始 dev 接力，7 次 resubmit 到 epoch 30
- P0-B：rsync MT models 到 Nano4，跑 benchmark，拿 throughput + peak GPU 數字
- P0-C：下載 HMP SRR072232，跑 NT-v2 sp_v4 推論（如果老師確認這個要做）

**完成後**：
- DNABERT-2 50M 跑完 → run eval_rc_tta → 更新 Table 4.x
- MT benchmark 完成 → 填入論文 §4.speed 的具體數字
- 更新 thesis figures + tables → compile → 準備 defense

**時程**：
- 6/15 thesis defense
- 6/30 論文繳交
- 7-8 月把 Chapter 4 改寫成 Bioinformatics 投稿格式
- 8/31 目標投出

以上，請老師確認 Q1、Q2、Q3 的方向，謝謝。

---

## 備用 Q&A

**Q：DNABERT-2 epoch 17 的 59% 跟 NT-v2 64% 差距會縮小嗎？**

不確定，但不樂觀。DNABERT-2 是 BPE tokenizer，不是 k-mer，在 DNA 上的 tokenization
效率本來就不如 k-mer。5M 版本已經比 NT-v2 5M 低了 3 pp，50M 可能維持類似差距。
不過還是要跑到 epoch 30 才能確認是否有 late convergence。

**Q：MT benchmark 的 throughput 預計多少？**

從 Taiwana-2 的 preliminary timing log，MT 13-mer 大約 8,000-12,000 reads/sec on V100。
H200 大概快 2-3 倍，估計 20,000+ reads/sec。
NT-v2 因為模型大 100 倍，大約 1,000-2,000 reads/sec。
這個差距是我們論文裡「light-weight 替代方案」論點的核心支撐。

**Q：如果 MT benchmark 數字很好，有沒有辦法在 defense 前把它加進去？**

有，就是這週 P0-B 的目標。跑完一個 dev job（1 小時）就有所有數字。
可以在 6/10-11 前拿到，來得及更新 thesis。

**Q：HMP 的 ground truth 是怎麼定義的？**

SRR072232 是 staggered mock community，20 種細菌已知比例。
我們輸出的 per-sample abundance 跟 known profile 算 Pearson r 跟 Bray-Curtis distance，
以及 sensitivity @ 95% specificity（ROC-based）。這三個指標在 MetaPhlAn 論文裡都有用過，
review 比較不會有疑慮。

**Q：Nano4 free trial 到什麼時候？**

setup 日期是 6/2，免費一個月，估計到 7/2 左右。
6/15 defense + 6/30 繳交都在範圍內，安全。
